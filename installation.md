---
layout: page
title: Installation
nav_order: 2
has_toc: true
permalink: /installation
---

# Installation
{: .no_toc}

Disclaimer: Gini5 has been tested development on Ubuntu 18.04 LTS "Bionic Beaver" and Linux Mint 19.2 "Tina". If you're running other Linux distribution, some components of Gini might not work properly.

## Table of contents
{: .no_toc .text-delta }

- TOC
{:toc}

## Python

Gini5 uses Python 2.7. In your terminal, enter the following command:

```bash
sudo apt-get install python-minimal
```

## Cloning the repository

Run these commands to clone the repository and set up your environment variable to run Gini components:

```bash
git clone https://github.com/citelab/gini5

cd gini5
echo "export GINI_HOME=$PWD" >> ~/.bashrc
echo 'export PATH=$PATH:$GINI_HOME/bin/' >> ~/.bashrc
source $HOME/.bashrc
```

## Installing dependencies

To install Gini5, you need to following libraries and applications:

```bash
sudo apt-get install libreadline-dev \
         python-lxml \
         python-qt4 \
         scons \
         screen \
         g++ \
         openssh-server \
         build-essential \
         xterm \
         libcanberra-gtk-module \
         libcanberra-gtk3-module \
         iproute2 \
         bridge-utils

python -m pip install ipaddress

# run these commands to download and compile libslack from source
wget http://libslack.org/download/libslack-0.6.tar.gz
tar xzf libslack-0.6.tar.gz
cd libslack-0.6
make
sudo make install
cd -

# allow non-root users to use `ip` and `brctl`"
sudo chmod a+s /sbin/brctl
sudo chmod a+s /sbin/ip
# "
```

## Docker installation

Consult the official Docker documentation on how to install Docker on your machine: https://docs.docker.com/install/

Gini is running Docker containers under the hood with the assumption that your user account has enough permission to use Docker. After installing, run the command `docker run hello-world`, if there is an error message saying that you don't have permission to run Docker, please follow the instructions here: https://docs.docker.com/install/linux/linux-postinstall/, or run these two commands:

```bash
sudo groupadd docker
sudo usermod -aG docker $USER
```

To pull the Docker images that Gini uses, run the script available under `scripts`:

```bash
./scripts/setup_docker.sh
```

## Setting up SSH

Change directory to `$HOME/.ssh` and run `ssh-keygen -t rsa` in that directory. When prompted, keep pressing ENTER to select the default options. Finally, run `cat id_rsa.pub >> authorized_keys`

## Plugins

### Wireshark

Please follow the instruction in https://www.wireshark.org/docs/wsug_html_chunked/ChapterBuildInstall.html. In the best case, you only need to run:

```bash
sudo add-apt-repository ppa:wireshark-dev/stable
sudo apt-get update
sudo apt-get install -y wireshark
```

To use wireshark to capture packets as a normal user, you need to add yourself to `wireshark` group on your machine, similar to Docker. Run these commands:

```
sudo dpkg-reconfigure wireshark-common
sudo usermod -a -G wireshark $USER
```

then try to log out and re-login for the change to take effect.

You can refer to this page for more information: https://wiki.wireshark.org/CaptureSetup/CapturePrivileges

### OpenvSwitch

Reference : http://docs.openvswitch.org/en/latest/intro/install/

If you want to try out Software Defined Networking (SDN) feature of Gini, first install two packages `openvswitch-switch` and `openvswitch-common`:

```bash
sudo apt-get install -y openvswitch-switch \
        openvswitch-common

# And add setuid bit to the programs that Gini uses:
sudo chmod a+s /usr/bin/ovs-vsctl
sudo chmod a+s /usr/bin/ovs-ofctl
sudo chmod a+s /usr/bin/ovs-docker
```

## Building Gini components

In the Gini directory, run the following commands:

```bash
scons
scons install
```

This should install GINI unless you get some errors in one or more of the above steps.
Once installed, issue the `gbuilder` command to start the graphical interface.

## Post-installation

- Check docker is properly installed by running `docker ps`. You will see a listing of docker containers that are running for that command. Because there are none running at this time, you will see an empty list with a header.
- Check the ssh passwordless login by running `ssh localhost`. You should be able to login without password with the proper key setup. If not, check the SSH key configuration.
- Optionally, if you want to enable mouse scrollwheel when using the devices' terminal in gBuilder, add this line to `~/.screenrc`:
```
termcapinfo xterm* ti@:te@
```

