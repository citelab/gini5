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

The first command was creating a `docker` group assuming that it did not exist before. The second command was adding your account to the docker group. 

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

Please follow the instructions of the case that best suits you.

1) The front-end and back-end are running on the same machine:
- Change directory to $HOME/.ssh
- Enter "ssh-keygen -t rsa" into the command line
- Press ENTER for all options
- Enter "cat id_rsa.pub >> authorized_keys" into the command line

2) The front-end and back-end are running on two different Linux machines:
- Change directory to $HOME/.ssh on the front-end
- Enter "ssh-keygen -t rsa" into the command line
- Enter "scp id_rsa.pub user@host1:.ssh/host2.pub" into the command line, where host1 is your back-end, host2 is your front-end and user is your username
- Change directory to $HOME/.ssh on the back-end
- Enter "cat host2.pub >> authorized_keys" into the command line

3) The front-end is running on Windows:
- Change directory to $HOME/.ssh on the back-end
- Enter "ssh-keygen -t rsa" into the command line
- Enter "cat id_rsa.pub >> authorized_keys" into the command line
- Copy the file $HOME/.ssh/id_rsa to the front-end
- Download puttygen (http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html)
- Load the file id_rsa into puttygen
- Choose 'Save private key' in puttygen
- Open putty
- Expand the 'SSH' category on the left
- Select 'Auth' and provide the .ppk file you saved earlier
- Scroll back up and select the 'Session' category on the left

If you only use putty with this program:
- Select 'Default Settings' under 'Saved Sessions'
- Press the 'Save' button

Details: What you just did was specify a key that putty will attempt to use by default anytime you use putty for SSH.  This is useful in gBuilder if you frequently change the server location to machines that will authenticate you the same way, such as machines within a school computer lab.

Otherwise, you should use Sessions:
- Specify the Host Name you want to associate with this session
- Specify a meaningful Session Name
- Press the 'Save' button

Details: What you just did was create a putty session identified by the name you provided.  This session holds the Host Name you will connect to, as well as the key used to authenticate you.  The session name can then be provided in gBuilder, who will use it to connect to the back-end.  Note that when providing a session name in gBuilder, the server name will be ignored.


# Notes

GINI should work on all Linux distributions with the required dependencies
installed.  If you have any problems on any distribution and/or
release, please e-mail the mailing list at gini@cs.mcgill.ca, or open an issue on this repository.
