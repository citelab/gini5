---
layout: page
title: REST API
parent: Gini5 features
nav_order: 5
---

# REST API for the Cloud component
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

- TOC
{:toc}


## Overview

To support students in developing networking projects that uses Gini, we provide a REST API for each active Cloud component of Gini in a network topology. All the commands that have been introduced in [Cloud]({{ site.baseurl }}/features/cloud) and [Service Function Chaining]({{ site.baseurl }}/features/service-function-chaining) will be available via the REST API. This section lists all the available endpoints, their parameters, as well as responses.


## Endpoints for Cloud

Note that for `POST` requests, the request body should be a JSON object. For all types of requests, you can expect a JSON object in the response.

### `GET /api/v1.0/cloud/list`

- Summary: Get a list containing all IDs of active cloud services
- Parameters: None
- Response:
    - `services`: A list consisting all IDs of cloud services

### `POST /api/v1.0/cloud/config/<string:serviceid>`

- Summary: Update the loadbalacing scheme of a cloud service
- Parameters:
    - `key`: The key to update, should be either `balance` or `mode`
    - `value`: The new value of the key. If `key` is `mode`, the value must be either `tcp` or `http`. If `key` is `balance`, the value should indicate a loadbalancing algorithm to be used. More detail on a list of algorithms can be found here: https://cbonte.github.io/haproxy-dconv/2.0/configuration.html#4.2-balance
    - `action`: If `PUT`, creates or updates the key. If `DELETE`, removes the key and let the service pick a default value
- Response:
    - `success`: A boolean value indicating whether the operation was successful

### `POST /api/v1.0/cloud/scale/<string:serviceid>`

- Summary: Modify the number of containers that a cloud service uses
- Parameters:
    - `size`: An integer indicating the new number of instances of this service
- Response:
    - `success`: A boolean value indicating whether the operation was successful

### `GET /api/v1.0/cloud/services/<string:serviceid>`

- Summary: Get detailed information about a cloud service
- Parameters: None
- Response:
    - `Containers`: A list of mapping, each mapping consists of a single key-value pair, where the key is the Docker container ID and the value is the name of the container
    - `Image`: The Docker image that the current service uses
    - `LB algorithm`: Loadbalancing algorithm used by the current service
    - `Mode`: Indicates whether loadbalancing is done on Layer 4 (TCP) or Layer 7 (HTTP)
    - `Number of containers`
    - `Port`: Indicate the port on which the current service is running
    - `Service name`: The ID of the service

### `DELETE /api/v1.0/cloud/services/<string:serviceid>`

- Summary: Remove an existing service
- Parameters: None
- Response:
    - `success`: A boolean value indicating whether the operation was successful

### `POST /api/v1.0/cloud/start`

- Summary: Start a new cloud service within this cloud instance
- Parameters:
    - `image`: The Docker image for this new cloud service
    - `name`: An ID for this service, must not clash with any existing service in the same cloud instance
    - `port`: The port this service is going to run on, must be a port that has not been used by any other service within the same instance
    - `scale`: The number of containers for this service. This value can be updated via another endpoint
    - `command`: The command used to run the Docker containers for this instance
- Response:
    - `success`: A boolean value indicating whether the operation was successful


## Endpoints for Service Function Chaining

### `POST /api/v1.0/sfc/init`

- Summary: Enable SFC features for this cloud instance. Note that the `service_function_chaining` component must be loaded in the POX controller for the features to work.
- Parameters: None
- Response:
    - `success`: A boolean value indicating whether the operation was successful

### `POST /api/v1.0/sfc/nodes`

- Summary: Create new VNF nodes
- Parameters:
    - `nodes`: A list of VNF node information, each is a JSON with the following structure:
        - `function`: Specify the type of VNF, e.g: firewall, monitor, rate-limiter, etc
        - `name`: A unique name that can be used to identify this node
- Response:
    - `success`: A boolean value indicating whether the operation was successful

### `GET /api/v1.0/sfc/nodes`

- Summary: Retrieve information about active VNF nodes
- Parameters: None
- Response: A mapping of node ID to its information, which includes the following:
    - `Interface`: MAC address and IP address of the VNF node
    - `Type`: The type of this node

### `DELETE /api/v1.0/sfc/nodes/<string:nodeid>`

- Summary: Remove an active VNF node
- Parameters: None
- Response:
    - `success`: A boolean value indicating whether the operation was successful

### `POST /api/v1.0/sfc/chains`

- Summary: Create new service function chains
- Parameters:
    - `chains`: A list of service function chain descriptions, each is a JSON with the following strcture:
        - `services`: A non-empty ordered list of node IDs to specify the service function chain to be created
- Response:
    - `success`: A boolean value indicating whether the operation was successful

### `GET /api/v1.0/sfc/chains`

- Summary: Get all service function chains information
- Parameters: None
- Response: A mapping of chain ID to list of VNF nodes, ordered according to their position in the service function chain

### `DELETE /api/v1.0/sfc/chains/<string:chainid>`

- Summary: Remove an existing service function chain
- Parameters: None
- Response:
    - `success`: A boolean value indicating whether the operation was successful

### `POST /api/v1.0/sfc/paths`

- Summary: Create new traffic routes through some SFC
- Parameters:
    - `paths`: A list of path descriptions, each is a JSON with the following structure:
        - `src`: The source of this path, use `Internet` to indicate traffic coming from external source. All traffic that comes from the source will be routed to go through the service function chain before reaching the destination
        - `dst`: The destination of this path
        - `chain`: The ID of the service function chain that traffic must go through
- Response:
    - `success`: A boolean value indicating whether the operation was successful

### `GET /api/v1.0/sfc/paths`

- Summary: Get all paths information
- Parameters: None
- Response:

### `DELETE /api/v1.0/sfc/paths/`

- Summary: Remove an existing SFC path
- Parameters:
    - `paths`: A list of path IDs, each is a JSON with the following parameters:
        - `src`: The source of this path
        - `dst`: The destination of this path
- Response:
    - `success`: A boolean value indicating whether the operation was successful

