# GINI Toolkit Version 5.0.0

The GINI Toolkit is free software. Please see the file COPYING for copyright information.


# Basic Installation - Ubuntu 18.04 LTS

GINI runs on Python2, so you may need to install if it does not come with your distribution. On Ubuntu 18.04, run the following command:

```bash
sudo apt-get install python-minimal
```

To install GINI, you need the following libraries and applications:

```bash
sudo apt-get install -y	libreadline-dev \
			python-lxml \
			python-qt4 \
			scons \
			screen \
			g++ \
			docker.io \
			openssh-server \
			build-essential \
			xterm \
			libcanberra-gtk-module \
			libcanberra-gtk3-module \
			iproute2 \
			bridge-utils
wget http://libslack.org/download/libslack-0.6.tar.gz
tar xzf libslack-0.6.tar.gz
cd libslack-0.6
make
sudo make install
```

Allow non-root users to use `ip` and `brctl` commands:

```bash
sudo chmod a+s /sbin/brctl
sudo chmod a+s /sbin/ip
```

A core component of GINI version 5 is Docker containers. You should installed Docker when you ran `sudo apt install docker.io` as required above. You need to setup the docker so that it would run without `sudo`. 
You can run the following commands to make Docker work without `sudo`. 

```bash 
sudo groupadd docker
sudo usermod -aG docker $USER
```

The first command was creating a `docker` group assuming that it did not exist before. The second command was adding your account to the docker group. After running this command, you may need to log out of your account and log back in (or reboot).

Clone the repository and set up PATH environment variable:

```bash
git clone -b uml-rename https://github.com/citelab/gini5
cd gini5
echo "export GINI_HOME=$PWD" >> ~/.bashrc
echo "export PATH=\$PATH:\$GINI_HOME/bin" >> ~/.bashrc
source $HOME/.bashrc
```

In the current directory, run the following commands:

```bash
scons
scons install
```

This should install GINI unless you get some errors in one or more of the above steps.
Once installed, issue the `gbuilder` command to start the graphical interface.

# SSH Key Generation instructions

Change directory to `$HOME/.ssh`
Run `ssh-keygen -t rsa` in that directory.
Press ENTER to select the default options.
Run `cat id_rsa.pub >> authorized_keys`.

# Some sanity checks

- Check docker is properly installed by running the following command.
`docker ps`
- You will see a listing of docker containers that are running for that command. Because there are none running at this time, you will see an empty list with a header. 
- Check the ssh password less login as follows.
`ssh localhost` 
- You should be able to login without password with the proper key setup. If not, check the SSH key configuration. 

# Notes

GINI should work on all Linux distributions with the required dependencies
installed.  If you have any problems on any distribution and/or
release, please e-mail maheswar@cs.mcgill.ca, or open an issue on this repository.
