# GINI Toolkit Version 3.0.0

[![Build Status](https://travis-ci.org/anrl/gini3.svg?branch=master)](https://travis-ci.org/anrl/gini3)

The GINI Toolkit is free software. Please see the file COPYING for copyright information.
Please read REPORT in this repository to know the functionalities.

Basic Installation - Ubuntu 16.04 LTS
==========================

<b>Ubuntu 14.04 is having some problems with the current version!</b>

To install GINI, you need the following libraries and applications:

	sudo apt-get install libreadline-dev
	sudo apt-get install python-lxml
	sudo apt-get install python-qt4
	sudo apt-get install scons
	sudo apt-get install screen
	sudo apt-get install uml-utilities
	sudo apt-get install openssh-server
    sudo apt-get install build-essential
    sudo apt-get install rxvt
	wget http://libslack.org/download/libslack-0.6.tar.gz
	tar xzf libslack-0.6.tar.gz
	cd libslack-0.6
	make
	sudo make install

Install each of these libraries, either through a package manager or
from source.  Libslack is unavailable on most, if not all, package 
managers, and must be installed from source.  It is available
at http://libslack.org/.

Once the libraries are installed, you must set the GINI_HOME environment 
variable to the location of your installation.  It is best to create
a separate directory, called "gini", where the GINI files will be installed.

The below instructions only work for the BASH shell.  To enter bash from 
another shell type "bash".

Create a "gini" directory in your home directory:

    mkdir $HOME/gini

Edit the .bashrc file (or create it if it's unavailable) in your home 
directory and add the following:

    export GINI_HOME=$HOME/gini
    export PATH=$PATH:$GINI_HOME/bin

This sets the GINI_HOME environment variable to your desired path, and
adds the bin directory within GINI_HOME to your PATH variable.

To enable the new settings, run the following:

    source $HOME/.bashrc

Now, get the gini source. You can issue the following command to get the gini source. Unpack gini source outside $GINI_HOME/gini (this is reserved for the GINI installation). You may create a directory such as $HOME/gini-src or something else of your liking.

    git clone git://github.com/anrl/gini3.git

Go into source directory and issue the following commands.

    scons 
    scons install

This should install GINI unless you get some errors in one or more of the above steps.
Once installed, issue the gbuilder command to start the graphical interface. 

Basic Installation - Windows
============================

On Windows, you can only install the frontend (gBuilder).
To install gBuilder, you need the following libraries and applications:

  * Required:
    TortoiseSVN (http://tortoisesvn.tigris.org)
    PuTTY (http://chiark.greenend.org.uk/~sgtatham/putty/download.html)
    - Must be added to %PATH% variable
    Python 2.5 or up (http://www.python.org)
    - Python 2.6 STRONGLY recommended
    - Must be added to %PATH% variable
    Scons 1.2 or up (http://www.scons.org)
    - Must be added to %PATH% variable (location: C:\Python2X\Scripts)
    PyQt 4.4 or up (http://www.riverbankcomputing.co.uk/software/pyqt/download)
    - PyQt 4.5 STRONGLY recommended
  * Optional:
    Matplotlib (http://matplotlib.sourceforge.net)
    Wireshark (http://www.wireshark.org)
    - Must be added to %PATH% variable

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

    scons install

This will install gBuilder into %GINI_HOME%.

If you have any problems installing gBuilder on Windows, please e-mail 
the mailing list at <gini at cs dot mcgill dot ca>.

SSH Key Generation instructions
===============================

Please follow the instructions of the case that best suits you.

1) The front-end and back-end are running on the same machine:
    -change directory to $HOME/.ssh
    -enter "ssh-keygen -t dsa" into the command line
    -press ENTER for all options
    -enter "cat id_dsa.pub >> authorized_keys" into the command line
    
2) The front-end and back-end are running on two different Linux machines:
    -change directory to $HOME/.ssh on the front-end
    -enter "ssh-keygen -t dsa" into the command line
    -enter "scp id_dsa.pub user@host1:.ssh/host2.pub" into the command line, where host1 is your back-end, host2 is your front-end and user is your username
    -change directory to $HOME/.ssh on the back-end
    -enter "cat host2.pub >> authorized_keys" into the command line
    
3) The front-end is running on Windows:
    -change directory to $HOME/.ssh on the back-end
    -enter "ssh-keygen -t dsa" into the command line
    -enter "cat id_dsa.pub >> authorized_keys" into the command line
    -copy the file $HOME/.ssh/id_dsa to the front-end
    -download puttygen (http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html)
    -load the file id_dsa into puttygen
    -choose 'Save private key' in puttygen
    -open putty
    -expand the 'SSH' category on the left
    -select 'Auth' and provide the .ppk file you saved earlier
    -scroll back up and select the 'Session' category on the left
    
If you only use putty with this program:
    -select 'Default Settings' under 'Saved Sessions'
    -press the 'Save' button
        
Details: What you just did was specify a key that putty will attempt to use by default anytime you use putty for SSH.  This is useful in gBuilder if you frequently change the server location to machines that will authenticate you the same way, such as machines within a school computer lab.
        
Otherwise, you should use Sessions:
-specify the Host Name you want to associate with this session
-specify a meaningful Session Name
-press the 'Save' button
        
Details: What you just did was create a putty session identified by the name you provided.  This session holds the Host Name you will connect to, as well as the key used to authenticate you.  The session name can then be provided in gBuilder, who will use it to connect to the back-end.  Note that when providing a session name in gBuilder, the server name will be ignored.

Wireless GINI integration
=====
Please refer to REPORT, https://github.com/ahmed-youssef/WirelessGINI and https://github.com/ahmed-youssef/yRouter for more information.

Notes
=====
The package "rxvt" might be needed, if already not available.
GINI should work on all linux distributions with the required dependencies 
installed.  If you have any problems on any distribution and/or 
release, please e-mail the mailing list at gini@cs.mcgill.ca
