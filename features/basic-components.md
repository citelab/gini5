---
layout: page
title: Basic networking components
parent: Gini5 features
nav_order: 1
---

# Basic Networking Components
{: .no_toc}

## Table of contents
{: .no_toc .text-delta}

- TOC
{:toc}

## Overview

Using the tool gBuilder, user of Gini is provided with an intuitive graphical interface to build and test network topologies. Here is an example of a running topology with 2 connected LANs in Gini. The active terminal is how user can control each network device in the network. In the image below, host machine `Mach_1` is sending pings to another host with IP `172.31.2.5`, located in another LAN.

![Overview of Gini5](/assets/images/gini-overview.png)

## Host machine (Mach)

This devide represents a physical host computer in a network topology. Under the hood, each host machine is a Docker container running custom built images. The containers are lightweight and equipped with some UNIX network utilities like iproute2, ping, traceroute, tcpdump, iptables, etc. Using host machine in a topology, user can test network connectivity, speed, dump packets, configure and send custom packets, etc.

After starting, user can double click the host machine icon in the topology to attach to the machine's terminal, where the mentioned commands can be used.

## Layer 2 Switch

This device uses Linux bridge underneath to simulate the behaviour of a physical switch operating on Layer 2. The configuration of this device is handled entirely by Gini.

## Router

This device acts as a Layer 3 switch to interconnect different Local Area Networks (LANs). gBuilder provides a command-line interface to configure a router device. From a router, you will be able to see the ARP table, ping other hosts in the network, and control the routing table.

## Subnet

In addition to simulating physical devices in a interconnected network, the subnet device is a logical entity that identifies a local area network. Subnet devices must be added to each LAN in order to assign Layer 3 addresses to each host and router. Since automatic IP assignment is enabled by default, the user does not have to take further steps than adding subnet to a topology.

The topology in [Overview](#overview) is comprised of 3 LANs, each has its own logical subnet device. These subnets have different IP ranges, since bridging is not yet supported in Gini5.

## Examples

TBU

