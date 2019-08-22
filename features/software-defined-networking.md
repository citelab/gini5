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

![Overview of Software-defined Networking](/assets/images/sdn-overview.png)

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

TBU

