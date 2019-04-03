#!/usr/bin/python
# -*- coding: utf-8 -*-

import docker
import os, sys
from cmd import Cmd
from inspect import cleandoc
import argparse
import json
import pprint


class GPrettyPrinter(pprint.PrettyPrinter, object):
    def format(self, obj, context, maxlevels, level):
        if isinstance(obj, unicode):
            return obj.encode("utf-8"), True, False
        return super(GPrettyPrinter, self).format(obj, context, maxlevels, level)


class GCloudShell(Cmd, object):
    """An interactive shell to manage gCloud, which is basically a Docker swarm node
    running in a single physical host

    Supported docker service commands:
        - docker service create
        - docker service ls
        - docker service ps
        - docker service rm
        - docker service scale
    """
    def __init__(self, subnet=None, gateway=None, *args, **kwargs):
        super(GCloudShell, self).__init__(*args, **kwargs)
        self.client = docker.from_env()
        # leave the current swarm, if there is any, and initialize a new swarm
        self.swarm_leave()
        self.swarm_init()
        self.pp = GPrettyPrinter(indent=2)

        ipam_pool = docker.types.IPAMPool(
            subnet=subnet,
            gateway=gateway
        )
        ipam_config = docker.types.IPAMConfig(
            pool_configs=[ipam_pool]
        )
        self.network = self.client.networks.create(
            "Gini_cloud_network",
            driver="overlay",
            scope="swarm",
            ipam=ipam_config,
            attachable=True
        )

    def swarm_init(self):
        """Initialize a docker swarm on the current machine"""
        try:
            self.client.swarm.init()
        except docker.errors.APIError:
            pass

    def swarm_leave(self):
        """Force leave a docker swarm"""
        try:
            self.client.swarm.leave(force=True)
        except docker.errors.APIError:
            pass

    @staticmethod
    def _parse_int(token):
        """Return an integer from a string token, return 0 if the token cannot
        be converted to int"""
        return int(token) if token.isdigit() else 0

    @staticmethod
    def _parse_dict(token):
        """Return a dictionary from a string token, result an empty dictionary
        if the string cannot be converted"""
        result = dict()
        try:
            result = json.loads(token)
        except ValueError:
            pass
        finally:
            return result

    @staticmethod
    def _parse_bool(token):
        """TODO"""
        pass

    @staticmethod
    def _parse_args(argv):
        """Parse all arguments from a command and return a dictionary of arguments-values.
        A valid argument has the form: --arg=value

        If more than one arguments with the same name is used, the last value will be used
        """
        values = dict()
        for token in argv:
            if token[:2] == "--":
                arg, value = token[2:].split("=", 1)
                values[arg] = value
        return values

    def _get_service(self, name):
        for service in self.client.services.list():
            if service.name == name:
                return service
        return None

    def do_create(self, args):
        """Create a service running on the cloud

        Usage: create IMAGE [--command="COMMAND"] [ARGS]"""
        argv = args.strip().split()
        if len(argv) == 0:
            self.stdout.write('Usage: create IMAGE [--command="COMMAND"] [ARGS]\n')
            return
        image = argv[0]
        kwargs = self._parse_args(argv[1:])
        try:
            kwargs["name"] = kwargs.get("name") or \
                "Gini_service"
            self.client.services.create(image, **kwargs)
        except docker.errors.APIError:
            self.stdout.write("Error: Cannot create a new service\n")

    def do_list(self, args):
        """List all running services

        Usage: list [--filters=FILTER_DICTIONARY]"""
        argv = args.strip().split()
        kwargs = self._parse_args(argv)
        try:
            kwargs["filters"] = self._parse_dict(kwargs.get("filters") or "")
            running_services = []
            for service in self.client.services.list(**kwargs):
                running_services.append("".join([
                    ("Short id: %s" % service.short_id).ljust(30),
                    ("Name: %s" % service.name).ljust(30),
                    ("Replicas: %d" % service.attrs["Spec"]["Mode"]["Replicated"]["Replicas"]).ljust(20),
                    "Image: %s" % service.attrs["Spec"]["TaskTemplate"]["ContainerSpec"]["Image"]]))
            self.stdout.write("\n".join(running_services) + "\n")
        except docker.errors.APIError:
            self.stdout.write("Error: Cannot list services\n")

    def do_get(self, args):
        """Retrieve information of a single running service

        Usage: get SERVICE_NAME"""
        argv = args.strip().split()
        if len(argv) == 0:
            self.stdout.write("Usage: get SERVICE_NAME\n")
            return
        name = argv[0]
        service = self._get_service(name)
        if service:
            self.pp.pprint(service.attrs)

    def do_remove(self, args):
        """Remove a running service

        Usage: remove SERVICE_NAME"""
        argv = args.strip().split()
        if len(argv) == 0:
            self.stdout.write("Usage: remove SERVICE_NAME\n")
            return
        name = argv[0]
        service = self._get_service(name)
        if service:
            try:
                service.remove()
            except docker.errors.APIError:
                self.stdout.write("Error: Cannot remove service\n")

    def do_scale(self, args):
        """Scale up/down a running service by changing the number of replicas

        Usage: scale SERVICE_NAME NUMBER_OF_REPLICAS"""
        argv = args.strip().split()
        if len(argv) < 2:
            self.stdout.write("Usage: scale SERVICE_NAME NUMBER_OF_REPLICAS\n")
            return
        name = argv[0]
        replicas = self._parse_int(argv[1])
        service = self._get_service(name)
        if service:
            if not service.scale(replicas):
                self.stdout.write("Warning: There was an issue scaling the service\n")

    def do_visualize(self, args):
        """Create a Docker visualization service, whose image is pulled from the
        Docker registry. It reports the status of every node inside a docker swarm.
        Access localhost:8080/ to see the result.

        Usage: visualize"""
        try:
            image = "dockersamples/visualizer:stable"
            kwargs = {
                "name": "Gini_visualizer",
                "endpoint_spec": docker.types.EndpointSpec(
                    ports={8080: (8080, "tcp", "ingress")}
                ),
                "networks": ["Gini_cloud_network"],
                "constraints": ["node.role==manager"],
                "mounts": ["/var/run/docker.sock:/var/run/docker.sock:ro"]
            }
            self.client.services.create(image, **kwargs)
        except docker.errors.APIError:
            self.stdout.write("Error: Cannot start visualize service\n")

    def do_exit(self, args):
        """Exit the shell

        Usage: exit | EOF"""
        self.swarm_leave()
        self.stdout.write("Bye\n")
        return True

    do_EOF = do_exit

    def do_help(self, arg):
        """List available commands with "help" or detailed help with "help cmd"."""
        if arg:
            # XXX check arg syntax
            try:
                doc=getattr(self, 'do_' + arg).__doc__
                if doc:
                    self.stdout.write("%s\n" % cleandoc(doc))
                    return
            except AttributeError:
                self.stdout.write("%s\n" % str(self.nohelp % (arg,)))
                return
        else:
            cmds = {}
            for name in self.get_names():
                if name[:3] == "do_":
                    cmd = name[3:]
                    cmds[cmd] = getattr(self, name).__doc__
            self.stdout.write("Interactive shell to manage open virtual switch through ovs-ofctl.\n\n")
            self.stdout.write("List of available commands:\n")
            # Calculate padding length
            col_width = max([len(word) for word in cmds.keys()]) + 4
            for key, value in cmds.items():
                self.stdout.write("\t%s%s\n" %
                                  (key.ljust(col_width), value.split("\n")[0]))

    def cmdloop(self, intro=None):
        """Override Cmd.cmdloop to add handler for SIGINT

        Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.
        """

        self.preloop()
        if self.use_rawinput and self.completekey:
            try:
                import readline
                self.old_completer = readline.get_completer()
                readline.set_completer(self.complete)
                readline.parse_and_bind(self.completekey+": complete")
            except ImportError:
                pass
        try:
            if intro is not None:
                self.intro = intro
            if self.intro:
                self.stdout.write(str(self.intro)+"\n")
            stop = None
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    if self.use_rawinput:
                        try:
                            line = raw_input(self.prompt)
                        except EOFError:
                            line = 'EOF'
                        except KeyboardInterrupt:
                            self.stdout.write("\nKeyboardInterrupt\n")
                            continue
                    else:
                        self.stdout.write(self.prompt)
                        self.stdout.flush()
                        line = self.stdin.readline()
                        if not len(line):
                            line = 'EOF'
                        else:
                            line = line.rstrip('\r\n')
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
            self.postloop()
        finally:
            if self.use_rawinput and self.completekey:
                try:
                    import readline
                    readline.set_completer(self.old_completer)
                except ImportError:
                    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gini Cloud program.")
    parser.add_argument("-s", "--subnet", type=str, metavar="", required=True,
                        help="Specify a subnet range for the cloud")
    parser.add_argument("-g", "--gateway", type=str, metavar="", required=False,
                        help="Specify a default gateway for the cloud network")
    arguments = parser.parse_args()

    try:
        shell = GCloudShell(subnet=arguments.subnet,
                            gateway=arguments.gateway)
        shell.cmdloop()
    except Exception as e:
        sys.stderr.write("Error occurred.\n")
        sys.stderr.write(str(e))
        exit(1)
