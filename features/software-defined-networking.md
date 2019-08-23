---
layout: page
title: Software-defined networking
parent: Gini5 features
nav_order: 2
---

# Software-Defined Networking
{: .no_toc}

## Table of contents
{: .no_toc .text-delta}

- TOC
{:toc}

## Overview

Software-defined networks (SDN) is an approach to computer networks that enables dynamic and efficiently programmable network configuration in order to improve network performance and monitoring. Gini5 offers its users a peek inside SDN technology by integrating OpenvSwitch (an open-source virtual switch) and POX controller into network topologies.

![Overview of Software-defined Networking]({{ site.baseurl }}/assets/images/sdn-overview.png)

## OpenvSwitch

In standalone mode, an OpenvSwitch (OVS) instance operates in the same way as how a physical L2 switch would do with a local MAC address to output port mapping. However, OVS is special because it is highly programmable, and can be used to bring in more dynamic routing to different network topologies.

Connection rules for OVS are quite similar to that of a normal switch, an addition to OVS is that it can be connected to SDN controllers (POX controllers) to listen for control commands.

More information about OpenvSwitch can be found in [the official documentation](https://docs.openvswitch.org/en/latest/) Gini5 provides a command-line interface to access each OVS instance in a network topology with some simplified shell commands.

| Command | Description |
|:--------|:-------|
| `show` | Show switch information, including information on its flow tables and ports |
| `dump [FLOW]` | Display specific flow rules that match `flows`, or all flows in the switch |
| `add FLOW` | Add a new flow entry to the current switch |
| `mod FLOW` | Modify the action in entries from the switch's table that match the specified flow |
| `del FLOW` | Delete a flow entry from the switch's flow tables |
| `help [COMMAND]` | Display help message |

## SDN Controller

Gini5 is using POX controller, which has an easy-to-use plugin system to customize and control virtual switches using OpenFlow protocol. When used in Gini5, POX is accessible via a command-line interface, which is actually a Python intepreter with some components already loaded.

More information about the project can be found in their official documentation: <https://noxrepo.github.io/pox-doc/html/>

## Examples

To demonstrate the ability of Software-Defined Networking, let's look at a simple topology:

<center>
    <img src="{{site.baseurl}}/assets/images/sdn-example-01.png" alt="SDN Topology">
</center>

This is a Local Area Network (LAN) with 3 hosts connected to the same OpenvSwitch (OVS), and the OVS is listening to a POX controller for instructions. OpenFlow is the protocol used between the switch and the controller. We start first by sending simple ICMP messages between hosts. From `Mach_1`'s terminal, enter the following command to ping `Mach_3`:

```sh
$ ping 172.31.0.4
```

Observe that the round-trip time for the first ICMP request-reply takes so much longer than the rest of the sequence. Initially, the OVS' flow tables are completely empty. When a packet comes in, instead of flooding and remember the input/output port like what a physical switch does, OVS asks the POX controller for instruction. After being told what to do by the controller, the OVS remembers this action and installs it as a flow rule in one of its flow tables and never has to come to the controller for that specific direction of traffic again, unless the installed flow has timed out. We can open the OVS' terminal and see the installed flow rule with the command `dump`:

```sh
$ dump
NXST_FLOW reply (xid=0x4):
cookie=0x0, duration=12.456s, table=0, n_packets=4, n_bytes=280, idle_age=7, dl_src=fe:fd:02:00:00:03,dl_dst=fe:fd:02:00:00:01 actions=output:3
cookie=0x0, duration=12.456s, table=0, n_packets=4, n_bytes=280, idle_age=7, dl_src=fe:fd:02:00:00:01,dl_dst=fe:fd:02:00:00:03 actions=output:2
```

The second and last line are 2 different flow rules. The first rule matches based on packets with source MAC `fe:fd:02:00:00:03` and destination MAC `fd:fd:02:00:00:01`. When those packets are sent to the OVS, the switch will output it to port 3, where the device with destination `fd:fd:02:00:00:01` is connected to the OVS. This is a very simply constructed flow rule. In reality, many more complicated flow rules exist and use matching on higher layer, or wildcards to match a subset of devices.

Suppose that we don't want to rely on the POX controller to guide the OVS, we can "program" the switches by ourselves. That is, we can manually set the flow rules in the switch's flow tables. Here is an example of setting the exact same flow rule as above by using the command `add` in the OVS's terminal. Before that, we also need to clear the flow tables:

```sh
$ del
$ add dl_src=fe:fd:02:00:00:03,dl_dst=fe:fd:02:00:00:01,actions=output:3
$ add dl_src=fe:fd:02:00:00:01,dl_dst=fd:fd:02:00:00:03,actions=output:2
```

Ping from `Mach_1` to `Mach_3` again, we can see that the round-trip time of the first trip doesn't take as long as when we need the POX controller.

You can actually write Python scripts to control how the POX controller works. When Gini is installed, it uses built-in modules to define the behaviour of the controller. If you want to try out different modules, simply right click the controller icon > Load modules and then choose one of them. The way the flow rules are installed will be different, sometimes no rules are installed. The custom > packet loss module is a good demonstration of how the modules differ from each other. To add your own POX controller module, look at their API documentation and some of the built-in modules first, then add a new Python script to `$GINI_HOME/lib/gini/pox/ext/gini/custom`. The API documentation has been linked in the section on [SDN controller](#sdn-controller).

