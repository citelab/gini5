---
layout: page
title: Cloud
parent: Gini5 features
nav_order: 3
---

# Cloud Component
{: .no_toc}

## Table of contents
{: .no_toc .text-delta}

- TOC
{:toc}

## Overview

To support the learning of cloud computing architecture, Gini5 has provided another component to the list of networks nodes: Cloud. With this addition, some concepts in cloud computing can be introduced more easily to students, such as service discovery, health checking, load balancing, scaling of services, etc.

When a cloud instance is started in Gini5, the following services are started in the backend:

- Proxy container: Uses [HAProxy](https://www.haproxy.com/) and [consul-template](https://github.com/hashicorp/consul-template) to act as a dynamically configurable reverse proxy
- Service registry: Uses [Consul](https://www.consul.io/) to store service information in the same private network
- Service registrator: Uses [Registrator](https://gliderlabs.github.io/registrator/latest/), or a custom Python script to perform automatic service discovery
- Other services: Can be multiple instances of HTTP, Email, FTP servers, generic compute engine, firewalls, etc running on different ports. These services use custom Docker images, which can be created and run by Gini users

![Overview of Cloud component]({{ site.baseurl }}/assets/images/cloud-overview.png)

## Proxy

The 'Cloud' in Gini5 is designed to be a group of hosts in a private LAN sitting behind a proxy server. The proxy server is assigned a static public IP address, which is reachable by every other communicating hosts from the Internet. In short, all traffic from outside ethe cloud network to internal services and vice versa has to go through this server. High availability is not yet supported, which means if the proxy is down for some reason, then the whole cloud instance is considered offline to the external network.

When the user double clicks a cloud icon in a running network topology, the IP address shown in the prompt is the proxy server's IP address, which can be used by external hosts to reach services from this cloud instance.

## Cloud services

The reason behind the proxy server is that you can deploy applications on multiple physical servers, but use only one IP address to access them, which gives the impression of running all those applications on a single machine. To external hosts, it does not make any difference at all. Service provider, however, can improve their applications' performance and high availability significantly, thanks to workloads being distributed to more compute resources. To make it simpler to develop, each services will be a bunch of containers running the same image and have some specified port exposed.

Some example Docker images that users of Gini5 can use as cloud services:

- `citelab/flask-server`: A simple Flask application that returns `hostname` and IP address of the container that is hosting the app.

## Service discovery and load balancing

Having a proxy as a gateway between internal services and the Internet, the proxy server needs to be aware of what services are running, how many containers belong to that service, and how to reach them should an external request comes in. After having that information, the proxy will be able to distribute requests to corresponding containers. This action is known as load balancing. In Gini5, Layer 4 load balancing is the default, although Layer 7 is also a feasible option.

In order to gather all necessary information about internal services, an action called service discovery is required, and this is done automatically by Gini's backend. The service 'registrator' is responsible for checking which container is being spawned, what service they are running and on which address and port they are listening. That registrator will then perform regular health check to update those containers' status. All information are stored in a service registry and notified to the proxy server. Based on the data, the proxy server will know how to give out workload accordingly.

## Using cloud manager command-line interface

While it might sound complicated, all the things mentioned above are just implementation details of how a cloud component is made up of in Gini5. The user is provided with a much more simple, intuitive command-line utility to monitor services running in a single cloud instance. Later on, this command-line interface is also what one would use for the [Service Function Chaining]({{ site.baseurl }}/features/service-function-chaining) feature of Gini5. Below is the list of available commands that can be used to manage services:

| Command | Description |
|:--------|:------------|
| `list` | List all running services within this cloud private LAN |
| `show SERVICE` | Show detailed information about an active service |
| `start IMAGE NAME PORT` | Start a service on this cloud instance, running the Docker image `IMAGE` with `PORT` exposed |
| `scale SERVICE SIZE` | Manually scale up/down a running service by adding/removing containers |
| `config SERVICE <mode|balance> VALUE` | Configure a service's load balancing scheme |
| `stop SERVICE` | Stop a running service |
| `stats` | Show services' statistics in a web browser |

## Examples

Let's investigate the network topology in [Overview](#overview) section. Note that the cloud must be the only host device in a LAN. All services provided by a cloud instance is accessible by any external host. The switch connecting all containers in the cloud private network can either be physical switch or virtual switch. In the case of virtual switch, [Service Function Chaining]({{site.baseurl}}/features/service-function-chaining) feature is also enabled.

To demonstrate two activities taking place in a cloud network: service discovery and load balancing. First build and run the network topology. When all components are up, enter either `Cloud_1` or `Cloud_2` command-line interface by double clicking their respective icons. Running the command `list` returns nothing, because no service is started yet. We now try to start an HTTP service in this cloud instance. The service will run on port 8080 and initially with 3 containers.

```sh
$ start citelab/flask-server:latest web 8080 --scale=3 --command=8080
$ list
web
$ show web
{
    "Image": "citelab/flask-server:latest",
    "Service name": "web",
    "Port": 8080,
    "Number of containers": 3,
    "Containers": [
        {
            "374f2bda8338": "web_01_Switch_1"
        },
        {
            "eb30f9ef0e52": "web_02_Switch_1"
        },
        {
            "6da53e3dd510": "web_03_Switch_1"
        }
    ],
    "Mode": "tcp",
    "LB algorithm": "roundrobin"
}
```

After the web service has been started successfully, we want to request its content from another host outside of that cloud network. Open `Mach_1`'s terminal and do the following a few times:

```sh
$ curl 172.31.0.254:8080
```

The 3 containers' information are returned on a Round-robin basis. Coincidence? Not really. Look at the "LB algorithm" key in the details for `web` service, it is specifying the load balancing algorithm for this service to be Round-robin. We can actually change that by using the `config` command in the cloud terminal:

```sh
$ config web balance first
Updated!
```

Try `curl` again, and the order of the returned hostnames may not be the same anymore. We can also change load balancing mode to layer 7 instead of the default layer 4, but that is outside the scope of this example.

If you want to write your own cloud service to use in Gini5, simply write and build a Docker image of your application and if necessary, push it on Docker Hub. Gini will be able to fetch and start it easily without needing to restart gBuilder.

