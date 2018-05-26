#!/bin/bash
scons -c
scons PREFIX=/gini-package/usr
mkdir -p gini-package/usr/share/applications
cp gini.desktop gini-package/usr/share/applications/
mkdir -p gini-package/usr/share/pixmaps
cp frontend/src/gbuilder/images/giniLogo.png gini-package/usr/share/pixmaps/
mkdir gini-package/DEBIAN
cp control gini-package/DEBIAN/
dpkg --build gini-package gini-2.1_i386.deb
scons -c
rm -rf gini-package
