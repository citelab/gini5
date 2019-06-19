#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-


from abc import ABC, abstractmethod
import docker
import ipaddress
from simplecloud import docker_client, docker_api_client, logger
from sortedcontainers import SortedSet
import subprocess


class BaseNetwork(ABC):
    @abstractmethod
    def add_container(self, container):
        ...

    @abstractmethod
    def remove_container(self, container):
        ...

    @abstractmethod
    def get_available_ip(self):
        ...

    @abstractmethod
    def reserve_ip(self, key, ipaddr=None):
        ...

    @abstractmethod
    def listen(self):
        ...

    @abstractmethod
    def reload(self):
        ...

    @abstractmethod
    def remove(self):
        ...

    @abstractmethod
    def resolve_ip(self, cid):
        ...

    @abstractmethod
    def stop_listening(self):
        ...


class BridgeNetwork(BaseNetwork):
    def __init__(self, network_name, subnet, reserved_ips=None):
        self._network = None
        self.ovs = False
        self.subnet = ipaddress.ip_network(subnet)
        self.address_pool = SortedSet(self.subnet.hosts())
        self.containers = dict()
        self.listening = False

        self.reservations = reserved_ips

        if not self.attach_to_existing_network(network_name):
            self.create_network(network_name)
        self.name = self._network.name

        self._handlers = {
            ('network', 'connect'): self.handler_network_connect,
            ('network', 'disconnect'): self.handler_network_disconnect
        }

    def attach_to_existing_network(self, name):
        network_list = docker_client.networks.list(names=[name])

        if len(network_list) > 0:
            logger.info('Existing Docker network found, attaching...')

            self._network = network_list[0]

            network_gateway = self._network.attrs['IPAM']['Config'][0].get('Gateway')

            if network_gateway:
                self._remove_ip(network_gateway)
            else:
                self.reservations['_'] = self._get_next_address()

            for cid, specs in self._network.attrs['Containers'].items():
                addr = specs['IPv4Address'][:-3]
                self.add_container(cid, addr)

            return True
        else:
            return False

    def create_network(self, name):
        ipam_pool = docker.types.IPAMPool(
            subnet=self.subnet.with_prefixlen,
        )

        ipam_config = docker.types.IPAMConfig(
            driver='default',
            pool_configs=[ipam_pool]
        )

        self._network = docker_client.networks.create(
            name=name,
            driver='bridge',
            ipam=ipam_config,
            attachable=True
        )

        # reserve one IP for the default gateway
        for ip in self.reservations.values():
            self._remove_ip(ip)
        self.reservations['_'] = self._get_next_address()

    def _get_next_address(self):
        if self.address_pool:
            next_addr = self.address_pool[0]
            self.address_pool.pop(0)

            logger.debug(f'Lending IP address {str(next_addr)}')
            return str(next_addr)
        else:
            logger.debug('No available IP address in the address pool')
            return None

    def get_available_ip(self):
        return self._get_next_address()

    def reserve_ip(self, key, ipaddr=None):
        if ipaddr:
            ip = self._remove_ip(ipaddr)
        else:
            ip = self._get_next_address()
        self.reservations[key] = str(ip)
        return str(ip)

    def _remove_ip(self, ip):
        addr = ipaddress.ip_address(ip)

        if addr not in self.subnet:
            raise ValueError

        try:
            self.address_pool.remove(addr)
            logger.debug(f'Address {ip} is now in use')
            return addr
        except KeyError:
            return None

    def _add_ip(self, ip):
        addr = ipaddress.ip_address(ip)
        self.address_pool.add(addr)
        logger.debug(f'Address {ip} is now available in the address pool')
        return addr

    def add_container(self, container, addr=None, reservation=None, register=None):
        reserved_ip = self.reservations.get(reservation)

        if reserved_ip:
            ipaddr = ipaddress.ip_address(reserved_ip)
        elif addr:
            ipaddr = self._remove_ip(addr)
        else:
            ipaddr = self._get_next_address()

        logger.debug(f'Connect container {container.id[:12]} to network')

        # docker network connect
        docker_api_client.connect_container_to_network(
            container.id, self._network.id, ipv4_address=str(ipaddr)
        )

        self.containers[container.id] = ipaddr

    def remove_container(self, cid):
        logger.debug(f'Disconnect container {cid[:12]} from network')

        try:
            docker_api_client.disconnect_container_from_network(
                cid, self._network.id, force=True
            )
        except docker.errors.APIError:
            pass

        ipaddr = self.containers.pop(cid, None)
        if ipaddr:
            self._add_ip(ipaddr)

    def handler_network_connect(self, event):
        if event['Actor']['ID'] == self._network.id:
            cid = event['Actor']['Attributes']['container']

            if cid in self.containers:
                return

            container = docker_client.containers.get(cid)
            networks = container.attrs['NetworkSettings']['Networks']
            ipaddr = networks[self._network.name]['IPAddress']

            logger.info(f'Network connect event with container {cid[:12]}')
            self.add_container(container, ipaddr)

    def handler_network_disconnect(self, event):
        if event['Actor']['ID'] == self._network.id:
            cid = event['Actor']['Attributes']['container']

            if cid not in self.containers:
                return

            logger.info(f'Network disconnect event with container {cid[:12]}')
            self.remove_container(cid)

    def listen(self):
        logger.info('Listening to Docker events...')

        self.listening = True

        self._network.reload()

        for event in docker_client.events(decode=True):
            if not self.listening:
                break
            func = self._handlers.get((event['Type'], event['Action']))
            if func:
                func(event)

    def reload(self):
        self._network.reload()

    def remove(self):
        self._network.remove()

    def stop_listening(self):
        self.listening = False

    def resolve_ip(self, cid):
        return str(self.containers[cid])


class OvsException(Exception):
    pass


class OpenVSwitchNetwork(BaseNetwork):
    def __init__(self, network_name, subnet, reserved_ips=None):
        self.name = network_name
        self.ovs = True
        self.subnet = ipaddress.ip_network(subnet)
        self.address_pool = SortedSet(self.subnet.hosts())
        self.containers = dict()
        self.registrator = None
        self.listening = False

        self.reservations = reserved_ips

        # reserve 1 IP address for the default gateway
        self.reservations['_'] = self._get_next_address()
        for _, ip in self.reservations.items():
            self._remove_ip(ip)

        if not self.check_bridge_exists():
            self.create_network(network_name)
        else:
            logger.debug('Bridge already exists, using it instead')

        self._handlers = {
            ('container', 'die'): self.handler_container_die,
            ('container', 'start'): self.handler_container_start
        }

    def check_bridge_exists(self):
        command = f'ovs-vsctl br-exists {self.name}'
        run = subprocess.Popen(command, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        run.communicate()

        return run.returncode == 0

    def create_network(self, name):
        gateway_ip = self.reservations['_']
        command = f'ovs-vsctl add-br {name} && \n'
        command += f'ip addr add {gateway_ip}/{self.subnet.prefixlen} dev {name} && \n'
        command += f'ip link set {name} up && \n'
        command += f'ovs-vsctl set-fail-mode {name} standalone'
        run = subprocess.Popen(command, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        _, err = run.communicate()
        if run.returncode != 0:
            logger.error(err.decode())
            raise OvsException(err.decode())

    def _get_next_address(self):
        if self.address_pool:
            next_addr = self.address_pool[0]
            self.address_pool.pop(0)

            logger.debug(f'Lending IP address {str(next_addr)}')
            return str(next_addr)
        else:
            logger.debug(f'No available IP address in the address pool')
            return None

    def get_available_ip(self):
        return self._get_next_address()

    def reserve_ip(self, key, ipaddr=None):
        if ipaddr:
            ip = self._remove_ip(ipaddr)
        else:
            ip = self._get_next_address()
        self.reservations[key] = str(ip)
        return str(ip)

    def _remove_ip(self, ip):
        addr = ipaddress.ip_address(ip)

        if addr not in self.subnet:
            raise ValueError

        try:
            self.address_pool.remove(addr)
            logger.debug(f'Address {ip} is now in use')
            return addr
        except KeyError:
            return None

    def _add_ip(self, ip):
        addr = ipaddress.ip_address(ip)
        self.address_pool.add(addr)
        logger.debug(f'Address {ip} is now available in the address pool')
        return addr

    def add_container(self, container, addr=None, reservation=None, register=False):
        reserved_ip = self.reservations.get(reservation)

        if reserved_ip:
            ipaddr = ipaddress.ip_address(reserved_ip)
        elif addr:
            ipaddr = self._remove_ip(addr)
        else:
            ipaddr = self._get_next_address()

        logger.debug(f'Connect container {container.id[:12]} to network')

        if register:
            self.registrator.register(container, str(ipaddr))

        # connect to ovs bridge
        command = f'ovs-docker add-port {self.name} eth1 {container.id[:12]} '
        command += f'--ipaddress={str(ipaddr)}/{self.subnet.prefixlen}'
        run = subprocess.Popen(command, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        out, err = run.communicate()

        #logger.debug(command)
        #logger.debug(out.decode())
        #logger.debug(err.decode())

        if run.returncode != 0:
            logger.error(f'Error while connecting container {container.id[:12]} to network')
            return OvsException('Failed while connecting container to network')
        else:
            self.containers[container.id] = ipaddr

    def remove_container(self, cid):
        logger.debug(f'Disconnect container {cid[:12]} from network')

        if self.listening:
            self.registrator.deregister(cid)

        command = f'ovs-docker del-port {self.name} eth1 {cid[:12]}'
        run = subprocess.Popen(command, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        run.communicate()

        if run.returncode != 0:
            logger.error(f'Error while removing container {cid[:12]} from network')
            raise OvsException('Failed while removing container from network')

        ipaddr = self.containers.pop(cid, None)
        if ipaddr:
            self._add_ip(ipaddr)

    def handler_container_start(self, event):
        # TODO: for fault tolerance, containers that are set to be restarted by Docker daemon
        # will not be connected to this network again, so we need to do something about it
        pass

    def handler_container_die(self, event):
        cid = event['Actor']['ID']

        if cid not in self.containers:
            return

        logger.info(f'Network disconnect event with container {cid[:12]}')
        self.remove_container(cid)

    def listen(self):
        logger.info('Listening to Docker events...')

        for event in docker_client.events(decode=True):
            if not self.listening:
                break
            func = self._handlers.get((event['Type'], event['Action']))
            if func:
                func(event)

    def reload(self):
        pass

    def remove(self):
        command = f'ovs-vsctl del-br {self.name}'
        run = subprocess.Popen(command, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        run.communicate()

    def stop_listening(self):
        self.listening = False

    def resolve_ip(self, cid):
        return str(self.containers[cid])

