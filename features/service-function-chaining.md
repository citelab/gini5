---
layout: page
title: Service function chaining
parent: Gini5 features
nav_order: 4
---

# Service Function Chaining
{: .no_toc}

## Table of contents
{: .no_toc .text-delta}

- TOC
{:toc}

## Overview

Service Function Chaining (SFC) refers to the use of Software-Defined Networking (SDN) programmability to create a service chain of connected (virtual) network services. One advantage of using SFC is to automate the way virtual network connections can be set up to handle different types of traffic flows. This image below from an SDXCentral article is an example of how SFC is set up and operate.

![SFC example]({{ site.baseurl }}/assets/images/sfc-overview.jpg)

In Gini5, the SFC feature is an extra component of POX controller and cloud instances. It can only be activated when a cloud instance is connected to an OVS, and the OVS is connected to a POX controller.

For further reading on Service Function Chaining design and architecture, you can visit these pages:

- SDXCentral's definition of SFC: <https://www.sdxcentral.com/networking/virtualization/definitions/what-is-network-service-chaining/>
- SDXCentral's definition of Virtual Network Function (VNF): <https://www.sdxcentral.com/networking/nfv/definitions/virtual-network-function/>
- Open Networking Foundation's documentation on SFC architecture: <https://www.opennetworking.org/wp-content/uploads/2014/10/L4-L7_Service_Function_Chaining_Solution_Architecture.pdf>

## Virtual network functions (VNF)

Similar to many virtualization techniques, VNF is an attempt to bring networking hardwares into compact and much more extensible software programs. Examples include firewalls, intrusion protection systems, network monitor, etc. Gini5 provides some lightweight virtual network functions, packaged into Docker images and make use of built-in UNIX networking utilities like `iptables`. It is very easy to add more custom VNF images as users want.

## Cloud manager and SDN controller

As introduced in previous section about [Cloud component]({{ site.baseurl }}/features/cloud), a cloud manager is a Python script capable of controlling all services running within a single cloud instance. In addition to handling all services, said program can also be used to manage VNF and SFC, as long as an SDN controller is present.

The SFC feature of Gini5 is quite simplified so some components of modern SFC might be missing, such as Network Service Headers (NSH). For the most part, the SDN controller (POX) has a component that communicates with the cloud manager to update what VNF is being added to the network, and what Service Chain is created in order to install flow rules in relevant virtual switches. VNF and SFC are specified by users, and routing is done in the background by the SDN controller. There are some terminologies used in Gini5 that may not be familiar:

- Service node: refers to a single instance of VNF, running in a Docker container
- Service chain: ordered list of service nodes
- Service path: path from a source machine to a destination machine that traverses a service chain in order. For example, the list `Host A -> Firewall -> IPS -> Rate limiter -> Host B` forms a service path with source A and destination B, and a service chain made up of 3 different VNFs in the middle.

## Using the cloud manager command-line interface

Here are the commands that can be used for SFC-related actions:

| Command | Description |
|:--------|:------------|
| `sfc_init` | This command MUST be used before using any other SFC-related commands |
| `sfc_addnode SERVICE NAME` | Create a new VNF instance |
| `sfc_delnode NAME` | Delete an active VNF instance |
| `sfc_listnode` | List all active VNF instances and display their information |
| `sfc_addchain SERVICE_LIST` | Create a service function chain from active VNF instances, the unique ID of the created chain will be returned on success |
| `sfc_delchain CHAIN_ID` | Delete an existing SFC using its unique ID |
| `sfc_listchain` | List all existing SFC and display their information |
| `sfc_addpath SRC DST CHAIN_ID` | Create a service path from source to destination that goes through a service chain. Either source or destination can be the Internet, which means all traffic from external network. Only one service path from source to destination can exist |
| `sfc_delpath SRC DST` | Delete a service path from source to destination |
| `sfc_listpath` | List all existing service paths and display their information |

## Examples

TBU

