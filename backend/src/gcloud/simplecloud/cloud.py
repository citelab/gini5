#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

"""This is a simple cloud program running docker containers. The program provides
an API to view and monitor services running in the cloud.

Core components:
- User-defined Docker bridge network
- Service registry (consul) container
- Service discovery container (registrator)
- TCP proxy (HAProxy) container, configured dynamically using consul-template
- Gateway: optional, used for communication between docker networks
- Additional web servers: can be created or scaled manually
"""

from simplecloud import docker_client, docker_api_client, logger
from simplecloud.network import BridgeNetwork, OpenVSwitchNetwork, OvsException
from simplecloud.registrator import Registrator
import requests
import base64
import traceback


proxy_configs = {
    'mode': ('tcp', 'http'),
    'balance': (
        'roundrobin', 'static-rr', 'leastconn',
        'first', 'source', 'uri', 'url_param', 'rdp-cookie'
    )
}


def _check_alive_container(container):
    try:
        container.reload()
        return container.status == 'running'
    except:
        return False


def _stop_container(container):
    try:
        logger.info(f'Stopping container {container.id}')
        container.remove(force=True)
    except:
        pass
    finally:
        return True


class MyCloudService:
    def __init__(self, image, name, network, port,
                 init_scale=1, command=None, is_ovs=False):
        self.image = image
        self.name = name
        self.port = port
        self.command = command

        self.network = network
        self.ovs = is_ovs

        self.containers = []
        self.idx = 1
        self.mode = None
        self.balance = None

        # start the current services with a number of running containers
        self.start(init_scale)

    @property
    def size(self):
        self.reload()
        return len(self.containers)

    def _create_container(self):

        host_config = docker_api_client.create_host_config(
            auto_remove=True,
            port_bindings={
                self.port: None
            }
        )

        pending_container = docker_api_client.create_container(
            image=self.image,
            name=f'{self.name}_{self.idx:02d}_{self.network.name}',
            command=self.command,
            detach=True,
            host_config=host_config,
            ports=[self.port],
            environment={
                'SERVICE_NAME': self.name,
                'SERVICE_ID': f'{self.name}_{self.idx:02d}'
            }
        )

        container = docker_client.containers.get(pending_container)
        self.idx += 1

        return container

    def _run_container(self):
        container = self._create_container()
        # order of operation may affect how registrator works
        if self.network.ovs:
            container.start()
            self.network.add_container(container, register=True)
        else:
            self.network.add_container(container)
            container.start()
        return container

    def info(self):
        _info = {
            "Image": self.image,
            "Service name": self.name,
            "Port": self.port,
            "Number of containers": self.size,
            "Containers": [
                {c.id[:12]: c.name} for c in self.containers
            ],
            "Mode": self.mode or 'tcp',
            "LB algorithm": self.balance or 'roundrobin'
        }

        return _info

    def start(self, scale):
        """Start the service with an initial number of containers"""
        for _ in range(scale):
            try:
                container = self._run_container()
                self.containers.append(container)
            except Exception as e:
                logger.error(e)

    def reload(self):
        """Refresh the docker client for up-to-date containers status"""
        self.containers = list(filter(_check_alive_container, self.containers))

    def scale(self, new_size):
        """Scale up or down the current service"""
        if new_size < 1:
            return False
        cur_size = self.size
        if new_size == cur_size:
            return True
        elif new_size < cur_size:
            # stop some running containers
            for container in self.containers[new_size:]:
                try:
                    self.network.remove_container(container.id)
                    _stop_container(container)
                except (OvsException,):
                    pass
            self.reload()
        else:
            # start new containers
            for _ in range(new_size - cur_size):
                try:
                    container = self._run_container()
                    self.containers.append(container)
                except Exception as e:
                    logger.error(e)
        return True

    def stop(self):
        """Stop all containers"""
        for container in self.containers:
            try:
                self.network.remove_container(container.id)
                _stop_container(container)
            except (OvsException,):
                pass
        self.containers = []

    def __str__(self):
        return f'Service: {self.name}'


class CloudException(Exception):
    pass


class MyCloud:
    def __init__(self, subnet=None, network_name=None, ovs=False, proxy_ip=None,
                 gateway_ip=None, initial_services=None, entrypoint=None):
        self.running = True

        # declare variables for network stuff
        self.proxy_ip = proxy_ip
        self.gateway_ip = gateway_ip

        reservations = {
            'proxy': proxy_ip,
            'gateway': gateway_ip
        }

        if not proxy_ip:
            reservations.pop('proxy')
        if not gateway_ip:
            reservations.pop('gateway')

        if ovs:
            self.network = OpenVSwitchNetwork(
                network_name,
                subnet,
                reservations
            )
        else:
            self.network = BridgeNetwork(
                network_name,
                subnet,
                reservations
            )

        self.registry_ip = self.network.reserve_ip('registry')
        logger.debug(f'registry ip requested: {self.registry_ip}')

        # create variables for important containers
        self.registry_name = "service-registry-%s" % network_name
        self.registrator_name = "service-registrator-%s" % network_name
        self.proxy_name = "proxy-%s" % network_name
        self.proxy_entrypoint = entrypoint
        self.registry = None
        self.registrator = None
        self.proxy = None
        self.services = {}
        self.used_ports = set()

        try:
            self.create_registry()
            self.create_proxy()

            self.proxy.start()
            self.network.add_container(self.proxy, reservation='proxy')
            self.proxy.exec_run('/root/entry/custom-entrypoint.sh')
            logger.info("Proxy has been started")

            self.registry.start()
            self.network.add_container(self.registry, reservation='registry')
            logger.info("Service registry has been started")

            if self.network.ovs:
                self.network.registrator = Registrator(self.registry)
            else:
                self.create_registrator()

            if self.registrator:
                self.network.add_container(self.registrator)
                self.registrator.start()
                logger.info("Service registrator has been started")

            if initial_services:
                self.initialize_services(initial_services)

        except Exception as e:
            logger.error(''.join(
                traceback.format_exception(
                    type(e), e, e.__traceback__)))
            self.cleanup()
            raise CloudException

    def create_registry(self):
        host_config = docker_api_client.create_host_config(
            restart_policy={
                "Name": "on-failure",
                "MaximumRetryCount": 10
            }
        )

        container = docker_api_client.create_container(
            image="citelab/consul-server:latest",
            command=["-bootstrap", f'-advertise={self.registry_ip}'],
            name=self.registry_name,
            host_config=host_config,
            detach=True
        )

        self.registry = docker_client.containers.get(container)

    def create_registrator(self):
        host_config = docker_api_client.create_host_config(
            restart_policy={
                "Name": "on-failure",
                "MaximumRetryCount": 10
            },
            binds=[
                "/var/run/docker.sock:/tmp/docker.sock"
            ]
        )

        container = docker_api_client.create_container(
            image="citelab/registrator:latest",
            command=["-internal",
                     "-explicit",
                     "-network=%s" % self.network.name,
                     "-retry-attempts=10",
                     "-retry-interval=1000",
                     "consul://%s:8500" % self.registry_ip],
            name=self.registrator_name,
            volumes=["/tmp/docker.sock"],
            host_config=host_config,
            detach=True
        )

        self.registrator = docker_client.containers.get(container)

    def create_proxy(self):

        if self.proxy_entrypoint:
            proxy_binds = ["%s:/root/entry/custom-entrypoint.sh" % self.proxy_entrypoint]
            proxy_volumes = ["/root/entry/custom-entrypoint.sh"]
            proxy_entrypoint = "/root/entry/custom-entrypoint.sh"
        else:
            proxy_binds = []
            proxy_volumes = []
            proxy_entrypoint = None

        host_config = docker_api_client.create_host_config(
            restart_policy={
                "Name": "on-failure",
                "MaximumRetryCount": 10
            },
            binds=proxy_binds,
            privileged=True
        )

        container = docker_api_client.create_container(
            image="citelab/haproxy:latest",
            entrypoint=proxy_entrypoint,
            command=[
                "consul-template",
                "-config=/tmp/haproxy.conf",
                "-consul=%s:8500" % self.registry_ip,
                "-log-level=debug"
            ],
            volumes=proxy_volumes,
            name=self.proxy_name,
            host_config=host_config,
            detach=True
        )

        self.proxy = docker_client.containers.get(container)

    @property
    def _registry_public_ip(self):
        self.registry.reload()

        return self.registry.attrs['NetworkSettings']['Networks']['bridge']['IPAddress']

    def registry_update(self, service, key, value=None, action='put'):
        if service not in self.services:
            return False
        if key not in proxy_configs or value not in proxy_configs[key]:
            return False

        # craft uri from arguments
        if self.network.ovs:
            uri = 'http://%s:8500/v1/kv/service/%s/%s' % (self._registry_public_ip, service, key)
        else:
            uri = 'http://%s:8500/v1/kv/service/%s/%s' % (self.registry_ip, service, key)
        if action == 'put' and value is not None:
            resp = requests.put(uri, data=value)
            if resp.json():    # success
                setattr(self.services[service], key, value)
                return True
            return False
        elif action == 'delete':
            resp = requests.delete(uri)
            if resp.json():
                setattr(self.services[service], key, None)
                return True
            return False
        else:
            return False

    def registry_get(self, service, key):
        # TODO
        if service not in self.services:
            return False
        if key not in proxy_configs:
            return False

        # craft uri from arguments
        if self.network.ovs:
            pass
        else:
            uri = 'http://%s:8500/v1/kv/service/%s/%s'
        resp = requests.get(uri)

        # returns default values if key does not exists
        if resp.status_code == 404:
            return 'tcp' if key == 'mode' else 'roundrobin'
        else:
            value = resp.json()[0]['Value']
            return base64.b64decode(value)

    def start_service(self, image, name, port, scale=1, command=None):
        if name in self.services:
            logger.warning(f"Service {name} already exists")
            return
        if port in self.used_ports:
            logger.warning(f"Port {port} has already been used!")
            return
        new_service = MyCloudService(
            image, name, self.network,
            port, scale, command)
        self.services[name] = new_service
        self.used_ports.add(port)

    def initialize_services(self, services_list):
        for service in services_list:
            self.start_service(**service)

    def stop_service(self, name):
        old_service = self.services.pop(name, None)
        if old_service:
            old_service.stop()
            self.used_ports.remove(old_service.port)
            logger.info(f"Removed service: {old_service.name}")
            return True
        logger.warning(f"Service {name} does not exist")
        return False

    def list_services(self):
        return self.services.keys()

    def info_service(self, name):
        if name in self.services:
            return self.services[name].info()
        else:
            return {}

    def scale_service(self, name, size):
        if name in self.services:
            return self.services[name].scale(size)
        else:
            return False

    def _update(self):
        self.network.reload()
        for container in (self.registry, self.registrator, self.proxy):
            container.reload()
        for service in self.services.values():
            service.reload()

    def cleanup(self):
        logger.debug("Cleaning up everything")
        self.network.stop_listening()
        for container in (self.registry, self.registrator, self.proxy):
            try:
                self.network.remove_container(container.id)
                _stop_container(container)
            except:
                continue
        for service in self.services.values():
            service.stop()
        try:
            self.network.remove()
        except:
            pass

        self.running = False
        logger.debug("Removed running services and docker network")
