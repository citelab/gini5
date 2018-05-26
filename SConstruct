# -*- python -*-
#
# GINI Version 2.2
# (C) Copyright 2009, McGill University
#
# Scons compile script for creating GINI installation
#
import os,os.path,stat
import shutil
import sys
import py_compile
from SCons.Node import FS
from subprocess import call

# Make sure git submodules are initialized
#call(["git", "submodule", "update", "--init", "--recursive"])



#import SconsBuilder

######################
# Shared Directories #
######################

# try:
#   gini_home = os.environ['GINI_HOME']
# except KeyError:
#   print "ERROR! The GINI_HOME environment variable not set."
#   print "Set GINI_HOME and rerun the installation script."
#   Exit(1)
# Export('gini_home')

src_dir = os.getcwd()

prefix = ARGUMENTS.get('PREFIX',"")
prefix = os.path.realpath(ARGUMENTS.get('DESTDIR',src_dir)) + prefix

build_dir = src_dir + "/build"

etcdir = prefix + "/etc"
bindir = prefix + "/bin"
libdir = prefix + "/lib/gini"
sharedir = prefix + "/share/gini"

#gini_src = os.getcwd()
#Export('gini_src')

###############
# Environment #
###############

env = Environment()

env.Clean(build_dir,build_dir)
env.Clean(bindir,bindir)
env.Clean(sharedir,sharedir)
env.Clean(sharedir,prefix + "/share")
env.Clean(libdir,libdir)
env.Clean(libdir,prefix + "/lib")

##################
# helper methods #
##################

def post_chmod(target):
  env.AddPostAction(target, "chmod +x " + target)

def actually_compile_python(target,source,env):
  py_compile.compile(source[0].abspath)

def compile_python(env,source,alias = None):
  env.Command(source + "c", source , actually_compile_python)
  if alias:
    env.Alias(alias,source + "c")

#####################
# Source Generators #
#####################

def gen_environment_file(target,source,env):
  output_file = open(target[0].abspath,'w')
  output_file.write('#!/usr/bin/python2\n')
  output_file.write('import os,subprocess,sys\n\n')
  output_file.write('previous_dir = os.getcwd()\n')
  output_file.write('os.chdir(os.path.dirname(os.path.realpath(__file__)))\n')
  output_file.write('os.environ["GINI_ROOT"] = os.path.realpath("%s")\n' % os.path.relpath(prefix,bindir))
  output_file.write('os.environ["GINI_SHARE"] = os.path.realpath("%s")\n' % os.path.relpath(sharedir,bindir))
  output_file.write('os.environ["GINI_LIB"] = os.path.realpath("%s")\n' % os.path.relpath(libdir,bindir))
  output_file.write('os.environ["GINI_HOME"] = os.environ["HOME"] + "/.gini"\n')
  output_file.write('if not os.path.exists(os.environ["GINI_HOME"] + "/etc"): os.makedirs(os.environ["GINI_HOME"] + "/etc")\n')
  output_file.write('if not os.path.exists(os.environ["GINI_HOME"] + "/sav"): os.makedirs(os.environ["GINI_HOME"] + "/sav")\n')
  output_file.write('if not os.path.exists(os.environ["GINI_HOME"] + "/data"): os.makedirs(os.environ["GINI_HOME"] + "/data")\n')
  output_file.write('if not os.path.exists(os.environ["GINI_HOME"] + "/tmp"): os.makedirs(os.environ["GINI_HOME"] + "/tmp")\n')
  output_file.write('params = [os.path.realpath("%s")]\n' % os.path.relpath(source[0].abspath,bindir))
  output_file.write('if len(sys.argv) > 1: params.extend(sys.argv[1:])\n')
  output_file.write('os.chdir(previous_dir)\n')
  output_file.write('os.execv(params[0],params)\n')
  return None

gen_environment_file_builder = Builder(action=gen_environment_file, single_target = True, single_source = True, target_factory = FS.File, source_factory = FS.File)

def gen_python_path_file(target,source,env):
  output_file = open(target[0].abspath,'w')
  output_file.write('import os\n')
  output_file.write('GINI_ROOT = "%s"\n' % prefix)
  #if env['PLATFORM'] != 'win32':
    #output_file.write('GINI_HOME = os.environ["HOME"] + "/.gini"\n')
  #else:
    #output_file.write('GINI_HOME = os.environ["USERPROFILE"] + "/gini_files"\n')
  output_file.write('GINI_HOME = "%s"\n'% prefix)
  output_file.close()
  return None

gen_python_path_builder = Builder(action=gen_python_path_file,
  single_target=True,
  target_factory = FS.File)

env.Append(BUILDERS = {'PythonPathFile':gen_python_path_builder})
env.Append(BUILDERS = {'PythonEnvFile':gen_environment_file_builder})

################
# Symlink Code #
################

def symlink(target, source, env):
  lnk = target[0].abspath
  src = source[0].abspath
  lnkdir,lnkname = os.path.split(lnk)
  srcrel = os.path.relpath(src,lnkdir)

  if int(env.get('verbose',0)) > 4:
    print 'target:', target
    print 'source:', source
    print 'lnk:', lnk
    print 'src:', src
    print 'lnkdir,lnkname:', lnkdir, lnkname
    print 'srcrel:', srcrel

  if int(env.get('verbose',0)) > 4:
    print 'in directory: %s' % os.path.relpath(lnkdir,env.Dir('#').abspath)
    print '    symlink: %s -> %s' % (lnkname,srcrel)

  try:
    os.symlink(srcrel,lnk)
  except AttributeError:
    # no symlink available, so we make a (deep) copy? (or pass)
    #os.copytree(srcrel,lnk)
    print 'no os.symlink capability on this system?'

  return None

def symlink_emitter(target,source,env):
  '''
  This emitter removes the link if the source file name has changed
  since scons does not seem to catch this case.
  '''
  lnk = target[0].abspath
  src = source[0].abspath
  lnkdir,lnkname = os.path.split(lnk)
  srcrel = os.path.relpath(src,lnkdir)

  if int(env.get('verbose',0)) > 3:
    ldir = os.path.relpath(lnkdir,env.Dir('#').abspath)
    if rellnkdir[:2] == '..':
        ldir = os.path.abspath(ldir)
    print '  symbolic link in directory: %s' % ldir
    print '      %s -> %s' % (lnkname,srcrel)

  try:
    if os.path.exists(lnk):
      if os.readlink(lnk) != srcrel:
          os.remove(lnk)
  except AttributeError:
    # no symlink available, so we remove the whole tree? (or pass)
    #os.rmtree(lnk)
    print 'no os.symlink capability on this system?'

  return (target, source)

symlink_builder = Builder(action = symlink,
    target_factory = FS.File,
    source_factory = FS.Entry,
    single_target = True,
    single_source = True,
    emitter = symlink_emitter)

env.Append(BUILDERS = {'Symlink':symlink_builder})

##########################
# Recursive installation #
##########################

def recursive_install(target, source, env):
    targets = []
    for root, dirnames, filenames in os.walk(source):
        for filename in filenames:
            tgt = env.Install(os.path.join(
                target, os.path.relpath(root, os.path.dirname(source))),
                os.path.join(root, filename))
            targets.append(tgt)
    return targets

##################
# Library checks #
##################

conf = Configure(env)
if not conf.CheckLib('slack'):
  print 'Did not find libslack.a or slack.lib, exiting!'
  Exit(1)
if not conf.CheckLib('readline'):
  print 'Did not find libreadline.so or readline.lib, exiting!'
  Exit(1)
if not conf.CheckLib('pthread'):
  print 'Did not find libpthread.so or pthread.lib, exiting!'
  Exit(1)
env = conf.Finish()

Export('env')

###########
# Backend #
###########

backend_dir = src_dir + "/backend"

#######
# POX #
#######

pox_dir = src_dir + "/backend/third-party/pox"
pox_ext_dir = src_dir + "/backend/src/pox/ext"
lib_pox_dir = libdir + "/pox"

pox_targets = recursive_install(libdir, pox_dir, env)

gpox = env.Symlink(bindir + "/gpox", lib_pox_dir + "/pox.py")
for target in pox_targets:
	env.Depends(gpox, target)

recursive_install(lib_pox_dir, pox_ext_dir, env)

###########
# grouter #
###########

grouter_include = backend_dir + '/include'
grouter_dir = backend_dir + '/src/grouter'
grouter_build_dir = src_dir + '/build/release/grouter'

VariantDir(grouter_build_dir,grouter_dir, duplicate=0)

grouter_env = Environment(CPPPATH=grouter_include)
grouter_env.Append(CFLAGS='-g')
grouter_env.Append(CFLAGS='-DHAVE_PTHREAD_RWLOCK=1')
grouter_env.Append(CFLAGS='-DHAVE_GETOPT_LONG')

# some of the following library dependencies can be removed?
# may be the termcap is not needed anymore..?
# TODO: libslack should be removed.. required routines should be custom compiled

grouter_libs = Split ("""readline
                         termcap
                         slack
                         pthread
                         util
                         m""")

grouter_test_objects = []
grouter_other_objects = []
for file in os.listdir(grouter_dir):
    if file.endswith(".c"):
        if file == "cli.c" or file == "grouter.c":
            grouter_other_objects.append(grouter_env.Object(grouter_build_dir + "/" + file))
        else:
            grouter_test_objects.append(grouter_env.Object(grouter_build_dir + "/" + file))

grouter = grouter_env.Program(grouter_build_dir + "/grouter", grouter_test_objects + grouter_other_objects, LIBS=grouter_libs)

env.Install(libdir + "/grouter/", grouter)
post_chmod(libdir + "/grouter/grouter")
env.PythonEnvFile(bindir + "/grouter" ,libdir + "/grouter/grouter")
post_chmod(bindir + "/grouter")

env.Install(sharedir + '/grouter/helpdefs', Glob(grouter_include + '/helpdefs/*'))

env.Alias('install-grouter',bindir + '/grouter')
env.Alias('install-grouter',sharedir + '/grouter/helpdefs')
env.Clean(bindir + "/grouter",libdir + "/grouter/grouter")
env.Clean("install-grouter",libdir + "/grouter")
env.Alias('install','install-grouter')

###########
# yRouter #
###########

yrouter_include = backend_dir + '/include'
yrouter_dir = backend_dir + '/src/grouter'
yrouter_build_dir = src_dir + '/build/release/yrouter'

VariantDir(yrouter_build_dir,yrouter_dir, duplicate=0)

yrouter_env = Environment(CPPPATH=yrouter_include)
yrouter_env.Append(CFLAGS='-g')
yrouter_env.Append(CFLAGS='-DHAVE_PTHREAD_RWLOCK=1')
yrouter_env.Append(CFLAGS='-DHAVE_GETOPT_LONG')

# some of the following library dependencies can be removed?
# may be the termcap is not needed anymore..?
# TODO: libslack should be removed.. required routines should be custom compiled

yrouter_libs = Split ("""readline
                         termcap
                         slack
                         pthread
                         util
                         m""")

yrouter_test_objects = []
yrouter_other_objects = []
for file in os.listdir(yrouter_dir):
    if file.endswith(".c"):
        if file == "cli.c" or file == "grouter.c":
            yrouter_other_objects.append(yrouter_env.Object(yrouter_build_dir + "/" + file))
        else:
            yrouter_test_objects.append(yrouter_env.Object(yrouter_build_dir + "/" + file))

yrouter = yrouter_env.Program(yrouter_build_dir + "/yrouter", yrouter_test_objects + yrouter_other_objects, LIBS=yrouter_libs)

env.Install(libdir + "/yrouter/", yrouter)
post_chmod(libdir + "/yrouter/yrouter")
env.PythonEnvFile(bindir + "/yrouter" ,libdir + "/yrouter/yrouter")
post_chmod(bindir + "/yrouter")

env.Install(sharedir + '/yrouter/helpdefs', Glob(yrouter_include + '/helpdefs/*'))

env.Alias('install-yrouter',bindir + '/yrouter')
env.Alias('install-yrouter',sharedir + '/yrouter/helpdefs')
env.Clean(bindir + "/yrouter",libdir + "/yrouter/yrouter")
env.Clean("install-yrouter",libdir + "/yrouter")
env.Alias('install','install-yrouter')


###########
# uswitch #
###########

uswitch_include = backend_dir + '/include/uswitch'
uswitch_dir = backend_dir + '/src/uswitch'
uswitch_build_dir = src_dir + '/build/release/uswitch'

VariantDir(uswitch_build_dir, uswitch_dir, duplicate=0)

uswitch_env = Environment(CPPPATH=uswitch_include)
uswitch = uswitch_env.Program(uswitch_build_dir + "/uswitch", Glob(uswitch_build_dir + "/*.c"))

env.Install(libdir + "/uswitch/", uswitch)
post_chmod(libdir + "/uswitch/uswitch")
env.PythonEnvFile(bindir + "/uswitch" ,libdir + "/uswitch/uswitch")
post_chmod(bindir + "/uswitch")

env.Alias('install-uswitch',bindir + '/uswitch')
env.Clean(libdir + "/uswitch",libdir + "/uswitch")
env.Alias('install','install-uswitch')

#########
# wgini #
#########

wgini_include = backend_dir + '/include/wgini'
wgini_dir = backend_dir + '/src/wgini'
wgini_build_dir = src_dir + '/build/release/wgini'

VariantDir(wgini_build_dir,wgini_dir, duplicate=0)

wgini_env = Environment(CPPPATH=wgini_include)
wgini_env.Append(CFLAGS='-DHAVE_PTHREAD_RWLOCK=1')
wgini_env.Append(CFLAGS='-DHAVE_GETOPT_LONG')

# some of the following library dependencies can be removed?
# may be the termcap is not needed anymore..?
# TODO: libslack should be removed.. required routines should be custom compiled
wgini_libs = Split ("""readline
    termcap
    slack
    pthread
    util
    m""")

gwcenter = wgini_env.Program(wgini_build_dir + "/gwcenter",Glob(wgini_build_dir + "/*.c"), LIBS=wgini_libs)

env.Install(libdir + "/wgini/", gwcenter)
post_chmod(libdir + "/wgini/gwcenter")
env.PythonEnvFile(bindir + "/gwcenter" ,libdir + "/wgini/gwcenter")
post_chmod(bindir + "/gwcenter")

env.Install(libdir + "/wgini/",wgini_dir + '/gwcenter.sh')
post_chmod(libdir + "/wgini/")
env.PythonEnvFile(bindir + "/gwcenter.sh", libdir + "/wgini/gwcenter.sh")
post_chmod(libdir + "/wgini/gwcenter.sh")

env.Alias('install-wgini',bindir + "/gwcenter")
env.Clean(libdir + "/wgini",sharedir + "/wgini")
env.Alias('install','install-wgini')

###########
# Gloader #
###########

gloader_dir = backend_dir + "/src/gloader"
gloader_conf = gloader_dir + "/gloader.dtd"
gloader_lib_dir = libdir

env.Install(sharedir + "/gloader/", gloader_conf)

result = env.Install(gloader_lib_dir + '/gloader', Glob(gloader_dir + "/*.py"))

for file in Glob(gloader_lib_dir + '/gloader/*.py'):
  compile_python(env,file.abspath,"install-gloader")
env.Clean(gloader_lib_dir + "/gloader",gloader_lib_dir + "/gloader")
post_chmod(gloader_lib_dir + "/gloader/gloader.py")
post_chmod(gloader_lib_dir + "/gloader/gserver.py")

env.PythonEnvFile(bindir + '/gserver',gloader_lib_dir + '/gloader/gserver.py')
post_chmod(bindir + '/gserver')
env.PythonEnvFile(bindir + '/gloader',gloader_lib_dir + "/gloader/gloader.py")
post_chmod(bindir + '/gloader')

env.Alias('install-gloader', sharedir + '/gloader')
env.Alias('install-gloader', gloader_lib_dir + '/gloader')
env.Alias('install-gloader', bindir + '/gloader')
env.Alias('install-gloader', bindir + '/gserver')
env.Alias('install-gloader', sharedir + '/gloader' + '/gloader.dtd')
env.Alias('install','install-gloader')

##########
# Kernel #
##########

# kernel_dir = backend_dir + "/kernel"
# kernel = kernel_dir + "/linux-2.6.26.1"
# alt_kernel = kernel_dir + "/linux-2.6.25.10"
#
# # Copy kernel and glinux loader into bin and set executable
# env.Install(libdir + '/kernel/',kernel_dir + '/glinux')
# post_chmod(libdir + '/kernel/glinux')
# env.PythonEnvFile(bindir + '/glinux',libdir + '/kernel/glinux')
# post_chmod(bindir + '/glinux')
#
# env.Install(libdir + '/kernel/', kernel_dir + '/linux-2.6.26.1')
# post_chmod(libdir + '/kernel/linux-2.6.26.1')
# env.PythonEnvFile(bindir + '/linux-2.6.26.1',libdir + '/kernel/linux-2.6.26.1')
# post_chmod(bindir + '/linux-2.6.26.1')
#
# env.Alias('install-kernel', bindir + '/glinux')
# env.Alias('install-kernel', bindir + '/linux-2.6.26.1')
# env.Clean(libdir + '/kernel/',libdir + '/kernel/')
# env.Alias('install','install-kernel')

##############
# FileSystem #
##############
#
# filesystem_dir = backend_dir + "/fs"
#
# filesystem_src = filesystem_dir + "/GiniLinux-fs-1.0q.tar.gz"
#
# # Unzip the gini UML fs into the root gini directory
# # TODO this is really bad
# env.Command(sharedir + '/filesystem/root_fs_beta2', filesystem_src, "tar -xzf " + filesystem_dir + "/GiniLinux-fs-1.0q.tar.gz --atime-preserve; cp -p GiniLinux-fs-1.0q $TARGET;rm GiniLinux-fs-1.0q")
#
# env.Alias('install-filesystem',sharedir + '/filesystem/root_fs_beta2')
# env.Clean(sharedir + '/filesystem',sharedir + '/filesystem')
# env.Alias('install','install-filesystem')

#########
# Vgini #
#########

vgini_dir = backend_dir + "/src/vgini"
vgini_build_dir = src_dir + "/build/release/vgini"

VariantDir(vgini_build_dir+"/local",vgini_dir+"/local", duplicate=0)
VariantDir(vgini_build_dir+"/remote",vgini_dir+"/remote", duplicate=0)

vproxy_env = Environment(CPPPATH= vgini_dir + "/local")
vproxy_env.Append(CFLAGS='-DHAVE_PTHREAD_RWLOCK=1')
vproxy_env.Append(CFLAGS='-DHAVE_GETOPT_LONG')

# some of the following library dependencies can be removed?
# may be the termcap is not needed anymore..?
# TODO: libslack should be removed.. required routines should be custom compiled
vproxy_libs = Split ("""readline
    slack
    pthread""")

vproxy = vproxy_env.Program(vgini_build_dir + "/local/vtproxy",Glob(vgini_build_dir + "/local/*.c"),LIBS=vproxy_libs)

env.Install(libdir + "/vgini/",vproxy)
post_chmod(libdir + "/vgini/vtproxy")
env.PythonEnvFile(bindir + "/vtproxy",libdir + "/vgini/vtproxy")
post_chmod(bindir + "/vtproxy")

vtap_env = Environment(CPPPATH= vgini_dir + "/remote")
vtap_env.Append(CFLAGS='-DHAVE_PTHREAD_RWLOCK=1')
vtap_env.Append(CFLAGS='-DHAVE_GETOPT_LONG')

# some of the following library dependencies can be removed?
# may be the termcap is not needed anymore..?
# TODO: libslack should be removed.. required routines should be custom compiled
vtap_libs = Split ("""readline
    slack
    pthread""")

vtap = vtap_env.Program(vgini_build_dir + "/remote/vtap",Glob(vgini_build_dir + "/remote/*.c"),LIBS=vproxy_libs)

env.Install(libdir + "/vgini/",vtap)
post_chmod(libdir + "/vgini/vtap")
env.PythonEnvFile(bindir + "/vtap",libdir + "/vgini/vtap")
post_chmod(bindir + "/vtap")

env.Alias('install-vgini',bindir + '/vtap')
env.Alias('install-vgini',bindir + '/vtproxy')
# env.Alias('install','install-vgini')
############
# Frontend #
############

frontend_dir = src_dir + "/frontend"

faq = '/doc/FAQ.html'

if env['PLATFORM'] == 'win32':
    dlls = env.Install(bindir, Glob(frontend_dir + "/bin/*"))
    env.Alias('install-windows', dlls)
    env.Alias('install','install-windows')
env.Install(prefix + '/doc', frontend_dir + faq)
env.Alias('install-doc', prefix + '/doc')
env.Clean(prefix + '/doc',prefix + '/doc')
env.Alias('install','install-doc')

############
# GBuilder #
############

gbuilder_dir = frontend_dir + "/src/gbuilder"

gbuilder_folders = Split("""
    Core
    Devices
    Network
    UI
    Wireless""")

gbuilder_images = gbuilder_dir + "/images/*"

env.Install(libdir + '/gbuilder/', gbuilder_dir + '/gbuilder.py')
compile_python(env,libdir + '/gbuilder/gbuilder.py',"install-gbuilder")

# Install each of the gbuilder folders
for x in gbuilder_folders:
  env.Install(libdir + '/gbuilder/' + x, Glob(gbuilder_dir + "/" + x + "/*.py"))
  for file in Glob(libdir + '/gbuilder/' + x + '/*.py'):
    compile_python(env,file.abspath,"install-gbuilder")
  env.Clean(libdir + "/gbuilder",libdir + "/gbuilder/" + x)
post_chmod(libdir + '/gbuilder/gbuilder.py')
# Install images
env.Install(sharedir + '/gbuilder/images/', Glob(gbuilder_images))
env.Clean(sharedir + '/gbuilder/images/',sharedir + '/gbuilder/images/')

post_chmod(libdir + "/gbuilder/Wireless/ServerAPI.py")
env.PythonEnvFile(bindir + '/ServerAPI',libdir + '/gbuilder/Wireless/ServerAPI.py')
post_chmod(bindir + '/ServerAPI')

env.Alias('install-gbuilder', bindir + '/ServerAPI')

if env['PLATFORM'] != 'win32':
    #env.SymLink(bindir + '/gbuilder', sharedir + '/gbuilder/gbuilder.py')
    env.PythonEnvFile(bindir + '/gbuilder', libdir + '/gbuilder/gbuilder.py')
    env.AddPostAction(bindir + '/gbuilder', "chmod +x " + bindir + '/gbuilder')
    env.Alias('install-gbuilder', bindir + '/gbuilder')
    # Adding Path info to gbuilder
env.Alias('install-gbuilder', sharedir + '/gbuilder')
env.Alias('install-gbuilder', libdir + '/gbuilder')
env.Clean(sharedir + '/gbuilder',sharedir + '/gbuilder')
env.Clean(libdir + '/gbuilder',libdir + '/gbuilder')
env.Alias('install', 'install-gbuilder')

##################
# Test Framework #
##################

test_dir = backend_dir + '/tests'
test_build_dir = src_dir + '/build/tests'
test_include = src_dir + '/backend/third-party/mut'
testenv = env.Clone()
testenv.Append(CPPPATH=[test_include])
testenv.Append(CFLAGS='-g')
testenv.Append(CFLAGS='-DHAVE_PTHREAD_RWLOCK=1')
testenv.Append(CFLAGS='-DHAVE_GETOPT_LONG')
testenv.VariantDir(test_build_dir, test_dir, duplicate=0)
tests = []

grouter_test_dir = test_dir + '/grouter'
grouter_test_build_dir = test_build_dir + '/grouter'
grouter_test_env = testenv.Clone()
grouter_test_env.Append(CPPPATH=[grouter_include])
grouter_test_env.VariantDir(grouter_test_build_dir, grouter_test_dir, duplicate=0)

for file in os.listdir(grouter_test_dir):
    if file.endswith("_t.c"):
        tests.append(grouter_test_env.Program(
            os.path.join(grouter_test_build_dir, file[:-2]),
            [os.path.join(grouter_test_build_dir, file)] + grouter_test_objects,
            LIBS=grouter_libs))

yrouter_test_dir = test_dir + '/grouter'
yrouter_test_build_dir = test_build_dir + '/yrouter'
yrouter_test_env = testenv.Clone()
yrouter_test_env.Append(CPPPATH=[yrouter_include])
yrouter_test_env.VariantDir(yrouter_test_build_dir, yrouter_test_dir, duplicate=0)

for file in os.listdir(yrouter_test_dir):
    if file.endswith("_t.c"):
        tests.append(yrouter_test_env.Program(
            os.path.join(yrouter_test_build_dir, file[:-2]),
            [os.path.join(yrouter_test_build_dir, file)] + yrouter_test_objects,
            LIBS=yrouter_libs))

test_alias = Alias('test', tests, [test[0].abspath for test in tests])
AlwaysBuild(test_alias)
