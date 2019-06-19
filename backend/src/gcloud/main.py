#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

from simplecloud import cloud, logger
from cmd import Cmd

import os
import sys
from threading import Thread
import webbrowser
import json
import argparse
import shlex
from inspect import cleandoc
from collections import defaultdict
import traceback
import signal


def _parse_int(token, default=0):
    """Returns an integer from a string token.
    Returns the default value if the token cannot be converted to int"""
    return int(token) if token.isdigit() else default


def _parse_dict(token, default=None):
    """Returns a dict from a string token
    Returns the default value if the token cannot be converted to dict"""
    try:
        result = json.loads(token)
        return result
    except ValueError:
        return default or {}


def _parse_args(argv):
    """Parses all arguments from a command and return a dictionary of arguments-values
    A valid argument has the form: --arg=value

    If more than one arguments with the same name is used, the last value will be used
    """
    values = defaultdict(str)
    new_argv = []
    for token in argv:
        if token[:2] == "--":
            arg, val = token[2:].split("=", 1)
            values[arg] = val
        else:
            new_argv.append(token)
    return values, new_argv


class CloudShell(Cmd, object):
    """Supported commands:
    - start
    - list
    - show (all, one service)
    - stop
    - scale"""
    def __init__(self, cloud_obj, *args, **kwargs):
        super(CloudShell, self).__init__(*args, **kwargs)
        self.cloud = cloud_obj
        self.prompt = "(%s) >> " % self.cloud.proxy_ip

    def cmdloop(self, intro=None):
        """Override Cmd.cmdloop to add handler for SIGINT
        Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.
        """
        os.system("clear")

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
                            line = input(self.prompt)
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
                try:
                    line = self.precmd(line)
                    stop = self.onecmd(line)
                    stop = self.postcmd(stop, line)
                except:
                    continue
            self.postloop()
        finally:
            if self.use_rawinput and self.completekey:
                try:
                    import readline
                    readline.set_completer(self.old_completer)
                except ImportError:
                    pass

    def _parse_start(self, line):
        argv = shlex.split(line)
        if len(argv) < 3:
            self.stdout.write("Usage: start IMAGE SERVICE_NAME PORT "
                              "[--scale=INITIAL_SCALE] [--command=COMMAND]\n")
            return None
        _kwargs, argv = _parse_args(argv)
        _parsed = {
            "image": argv[0],
            "name": argv[1],
            "port": _parse_int(argv[2], 80),
            "scale": _parse_int(_kwargs["scale"], 1),
            "command": _kwargs["command"]
        }

        return _parsed

    def do_start(self, line):
        """Start a service running on the cloud"

        Usage: start IMAGE NAME PORT [--scale=INITIAL_SCALE] [--command=COMMAND]

        By default, initial scale is 1"""
        _kwargs = self._parse_start(line)
        if not _kwargs:
            return
        else:
            try:
                self.cloud.start_service(**_kwargs)
            except Exception as e:
                self.stdout.write("Error occurred: %s\n" % str(e))
                return

    def _parse_stop(self, line):
        argv = shlex.split(line)
        if len(argv) == 0:
            self.stdout.write("Usage: stop SERVICE_NAME\n")
            return None
        return {"name": argv[0]}

    def complete_stop(self, text, *ignored):
        _services = self.cloud.list_services()
        return [name for name in _services if name.startswith(text)]

    def do_stop(self, line):
        """Stop a running service if exists

        Usage: stop SERVICE_NAME"""
        _kwargs = self._parse_stop(line)
        if _kwargs:
            self.cloud.stop_service(_kwargs["name"])

    def _parse_show(self, line):
        argv = shlex.split(line)
        if len(argv) == 0:
            self.stdout.write("Usage: show SERVICE_NAME\n")
            return None
        return {"name": argv[0]}

    def complete_show(self, text, *ignored):
        _services = self.cloud.list_services()
        return [name for name in _services if name.startswith(text)]

    def do_show(self, line):
        """Show information about a running service

        Usage: show SERVICE_NAME"""
        _kwargs = self._parse_show(line)
        if _kwargs:
            _info = self.cloud.info_service(_kwargs["name"])
            if not _info:
                self.stdout.write("Can't retrieve service information\n")
            else:
                self.stdout.write(json.dumps(_info, indent=2))
                self.stdout.write("\n")

    def do_list(self, line):
        """List all running services

        Usage: list"""
        services = self.cloud.list_services()
        self.stdout.write("\n".join(services) + "\n")

    def _parse_scale(self, line):
        argv = shlex.split(line)
        if len(argv) < 2:
            self.stdout.write("Usage: scale SERVICE_NAME SIZE")
            return None
        _kwargs = {
            "name": argv[0],
            "size": _parse_int(argv[1], 0)
        }
        return _kwargs

    def complete_scale(self, text, *ignored):
        argv = shlex.split(text)
        if len(argv) <= 1:
            _services = self.cloud.list_services()
            return [name for name in _services if name.startswith(text)]
        else:
            return []

    def do_scale(self, line):
        """Scale up/down a running service by adding/removing container

        Usage: scale SERVICE_NAME SIZE"""
        _kwargs = self._parse_scale(line)
        if _kwargs:
            self.cloud.scale_service(_kwargs["name"], _kwargs["size"])

    def _parse_config(self, line):
        argv = shlex.split(line)
        if len(argv) < 3:
            self.stdout.write("Usage: config SERVICE_NAME KEY VALUE [--action=<delete|put>]")
            return None
        _parsed, argv = _parse_args(argv)
        _action = _parsed.get("action", "put").lower()
        if _action not in ("put", "delete"):
            return None
        _kwargs = {
            "service": argv[0],
            "key": argv[1],
            "value": argv[2],
            "action": _action
        }
        return _kwargs

    def complete_config(self, text, line, *ignored):
        argv = shlex.split(line)
        if (len(argv) == 1 and not text) \
                or (len(argv) == 2 and text):
            _services = self.cloud.list_services()
            return [name for name in _services if name.startswith(text)]
        elif (len(argv) == 2 and not text) \
                or (len(argv) == 3 and text):
            _keys = cloud.proxy_configs.keys()
            return [k for k in _keys if k.startswith(text)]
        elif (len(argv) == 3 and not text) \
                or (len(argv) == 4 and text):
            _values = cloud.proxy_configs.get(argv[2], [])
            return [v for v in _values if v.startswith(text)]

    def do_config(self, line):
        """Configure a service's load balancing scheme

        Usage: config SERVICE_NAME <mode|balance> VALUE"""
        _kwargs = self._parse_config(line)
        if not _kwargs:
            return
        else:
            if self.cloud.registry_update(
                _kwargs["service"], _kwargs["key"],
                _kwargs["value"], _kwargs["action"]
            ):
                sys.stdout.write("Updated!\n")
            else:
                sys.stdout.write("Cannot update service\n")

    def do_stats(self, line):
        """Show statistics in a web browser

        Usage: stats"""
        url = 'http://%s:10000/stats' % self.cloud.proxy_ip
        webbrowser.open(url)

    def do_exit(self, line):
        """Remove cloud services and exit the shell

        Usage: exit | EOF"""

        if self.cloud.running:
            self.cloud.cleanup()
        return True

    do_EOF = do_exit

    def do_help(self, line):
        """List available commands with "help" or detailed help with "help cmd".

        Usage: help [COMMAND]"""
        if line:
            try:
                doc = getattr(self, 'do_' + line).__doc__
                if doc:
                    self.stdout.write("%s\n" % cleandoc(doc))
                    return
            except AttributeError:
                self.stdout.write("%s\n", str(self.nohelp % (line,)))
        else:
            cmds = {}
            for name in self.get_names():
                if name[:3] == "do_":
                    cmd = name[3:]
                    cmds[cmd] = getattr(self, name).__doc__
            self.stdout.write("Interactive shell to manage simple cloud services\n\n")
            self.stdout.write("List of available commands:\n")
            # Calculate padding length
            col_width = max([len(word) for word in cmds.keys()]) + 4
            for key, value in cmds.items():
                self.stdout.write("\t%s%s\n" %
                                  (key.ljust(col_width), value.split("\n")[0]))


class KeyNotFoundError(Exception):
    pass


def parse_file(config_path):
    if not os.path.isfile(config_path):
        raise IOError
    with open(config_path, "r") as f:
        try:
            configs = json.load(f, encoding="utf-8")
        except ValueError:
            raise ValueError("Configuration file is not in JSON format")

    # config file must contain subnet range
    if "subnet" not in configs:
        raise KeyNotFoundError("You need to specify the subnet range")

    logger.info(json.dumps(configs, indent=2, sort_keys=True))

    return configs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simple cloud program with a TCP proxy, "
                    "service registry and auto-discovery."
    )

    # accepts config file to specify network address and containers IP

    config_group = parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument("-f", "--config-file", type=str,
                              metavar="PATH", dest="config",
                              help="Specify path to config file")
    config_group.add_argument("-s", "--subnet", type=str, metavar="IP_RANGE",
                              help="Specify a subnet range for the cloud. Use CIDR format")

    parser.add_argument("-n", "--net-name", type=str, metavar="NETWORK_NAME",
                        default="my_network", dest="network_name",
                        help="Name the user-defined Docker network")
    parser.add_argument("-p", "--proxy-ip", type=str,
                        metavar="PROXY_IP", dest="proxy_ip",
                        help="Reserve an IPv4 address for proxy container")
    parser.add_argument("-g", "--gateway-ip", type=str,
                        metavar="GATEWAY_IP", dest="gateway_ip",
                        help="Reserve an IPv4 address for the gateway")

    validate_group = parser.add_mutually_exclusive_group()
    validate_group.add_argument("--validate-ip", dest="validate", action="store_true",
                                help="Validate configurations after parsing")
    validate_group.add_argument("--no-validate-ip", dest="validate", action="store_false",
                                help="Skip validation of configurations")

    parsed = parser.parse_args()

    if parsed.config:
        kwargs = parse_file(parsed.config)
    else:
        kwargs = vars(parsed)

    my_cloud = None

    def sigterm_handler(_signo, _stack_frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    try:
        logger.debug("Starting services...")

        my_cloud = cloud.MyCloud(**kwargs)

        logger.debug("Everything is up")
        cloud_shell = CloudShell(my_cloud)

        def listener_loop():
            my_cloud.network.listen()

        t = Thread(target=listener_loop, daemon=True)
        t.start()

        cloud_shell.cmdloop()

    except Exception as e:
        logger.error(''.join(
                traceback.format_exception(
                    type(e), e, e.__traceback__)))
    finally:
        if my_cloud and my_cloud.running:
            my_cloud.cleanup()
        logger.info('Bye')
        sys.exit()
