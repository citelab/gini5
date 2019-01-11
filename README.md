# GINI Toolkit Version 5.0.0

The GINI Toolkit is free software. Please see the file COPYING for copyright information.
Please read REPORT in this repository to know the functionalities.

# Basic Installation - Ubuntu 18.04 LTS

GINI runs on Python2, so you may need to install if it does not come with your distribution. On Ubuntu 18.04, run the following command:

```bash
	sudo apt-get install python-minimal
```

To install GINI, you need the following libraries and applications:

```bash
	sudo apt-get install	libreadline-dev \
							python-lxml \
							python-qt4 \
							scons \
							screen \
							openssh-server \
							build-essential \
							rxvt \
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

A core component of GINI version 5 is Docker containers. To install Docker on your local machine, please refer to the documentation: https://docs.docker.com/install/. Once installed, make sure that your non-root users can run Docker commands without any error.

Install each of these libraries, either through a package manager or
from source. Libslack is unavailable on most, if not all, package
managers, and must be installed from source.  It is available
at http://libslack.org/.

Clone the repository and set up PATH environment variable:

```bash
	git clone https://github.com/anrl/gini5.git
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

# Basic Installation - Windows

On Windows, you can only install the frontend (gBuilder).
To install gBuilder, you need the following libraries and applications:

* Required:
	- TortoiseSVN (http://tortoisesvn.tigris.org)
	- PuTTY (http://chiark.greenend.org.uk/~sgtatham/putty/download.html)
	Must be added to %PATH% variable
	- Python 2.5 or up (http://www.python.org)
	Python 2.6 STRONGLY recommended
	Must be added to %PATH% variable
	- Scons 1.2 or up (http://www.scons.org)
	Must be added to %PATH% variable (location: C:\Python2X\Scripts)
	- PyQt 4.4 or up (http://www.riverbankcomputing.co.uk/software/pyqt/download)
	PyQt 4.5 STRONGLY recommended
* Optional:
	- Matplotlib (http://matplotlib.sourceforge.net)
	- Wireshark (http://www.wireshark.org)
	Must be added to %PATH% variable

Once the libraries are installed, you must set the GINI_HOME environment
variable to the location of your installation.  It is best to create
a separate directory, called "gini", where the GINI files will be installed.

Add a user variable called GINI_HOME, and point that to the location you want
to install to.  Also, edit the system variable 'Path' to include
[location of GINI_HOME]\bin.

Now we are ready to configure and install GINI.  You can use TortoiseSVN
to grab the latest frontend code.  In the SVN Checkout dialog box, set
"URL of repository" to https://svn.origo.ethz.ch/gini/stable/frontend and
"Checkout directory" to a build location of your choice.

Within the directory where you checked-out the source code, run the
following command in the Command prompt (scons must be in the %PATH% variable):

```
	scons install
```

This will install gBuilder into %GINI_HOME%.

If you have any problems installing gBuilder on Windows, please e-mail
the mailing list at <gini at cs dot mcgill dot ca>.

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
- specify the Host Name you want to associate with this session
- specify a meaningful Session Name
- press the 'Save' button

Details: What you just did was create a putty session identified by the name you provided.  This session holds the Host Name you will connect to, as well as the key used to authenticate you.  The session name can then be provided in gBuilder, who will use it to connect to the back-end.  Note that when providing a session name in gBuilder, the server name will be ignored.

# Wireless GINI integration

Please refer to REPORT, https://github.com/ahmed-youssef/WirelessGINI and https://github.com/ahmed-youssef/yRouter for more information.

# Notes

The package "rxvt" might be needed, if not already available.
GINI should work on all Linux distributions with the required dependencies
installed.  If you have any problems on any distribution and/or
release, please e-mail the mailing list at gini@cs.mcgill.ca, or open an issue on this repository.
