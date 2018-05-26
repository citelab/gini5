import os, sys, time, subprocess

remote_dir = "/root/"
local_dir = "/home/akanksha/"
sshpass = "sshpass -p \"akanksha1\""
username = "root"
password = "arduino"

class ifaces:
	def __init__(self, top_num, IP):
		self.top_num = top_num
		self.tun = []
		self.wlan = []
		self.StationIP = IP

	def AddTunIface(self, tuniface):
		self.tun.append(tuniface)

	def AddWlanIface(self, wlaniface):
		self.wlan.append(wlaniface)

class tun_iface:
	def __init__(self, num, dst_ip, dst_iface, vIP, vHW, routes):
		self.num = num
		self.dst_ip = dst_ip
		self.dst_iface = dst_iface
		self.vIP = vIP
		self.vHW = vHW
		self.routes = routes

	def AddRoute(self, routes):
		self.routes.append(routes)

class wlan_iface:
	def __init__(self, num, vIP):
		self.num = num
		self.vIP = vIP
		self.routes = []

	def AddRoute(self, routes):
		self.routes.append(routes)


class rentry:
	def __init__(self, net, netmask, nexthop):
		self.net = net
		self.netmask = netmask
		self.nexthop = nexthop

def run_yrouter(interfaces, ID):
	StationIP = interfaces.StationIP


	# 1) Set up the yrouter's configuration file
	configFileName = "script_t%d_y%d.conf" %(interfaces.top_num, ID)
	configFile = local_dir + configFileName
	# delete confFile if already exists
	if (os.access(configFile, os.F_OK)):
		os.remove(configFile)
	configfd = open(configFile, "w")

	outLine = ""
	for iface in interfaces.tun:
		outLine += "ifconfig add tun%d " % (iface.num)
		outLine += "-dstip %s -dstport %d -addr %s -hwaddr %s\n" \
		%(iface.dst_ip, iface.dst_iface, iface.vIP, iface.vHW)

		for route in iface.routes:
			outLine += "route add -dev tun%d -net %s -netmask %s" \
			%(iface.num, route.net, route.netmask)
			if(route.nexthop != "None"):
				outLine += " -gw %s" %route.nexthop
			outLine += "\n"
        outLine += "route add -dev tun%d -net 192.168.0.0 -netmask 255.255.255.0\n"%(iface.num)
	for iface in interfaces.wlan:
		outLine += "ifconfig add raw%d -addr %s\n" % (iface.num+1, iface.vIP)

		for route in iface.routes:
			outLine += "route add -dev raw%d -net %s -netmask %s" \
			%(iface.num+1, route.net, route.netmask)
			if(route.nexthop != "None"):
				outLine += " -gw %s" %route.nexthop
			outLine += "\n"

	configfd.write(outLine)
	configfd.close()

	# 2) Copy configuration file to remote Station
	RemoteFile = remote_dir + configFileName
	remote_Station = "root@%s" % StationIP
	remote_copy = "%s scp %s %s:%s" \
	%(sshpass, configFile, remote_Station, remote_dir)
	os.system(remote_copy)

	# 3) Run yrouter using ssh
	yrouter = "screen -d -m -L -S newrouter%s yrouter --interactive=1 \
	--config=%s test%s\n" %(interfaces.top_num, RemoteFile, interfaces.top_num)
	print yrouter
	remote_run = "%s ssh %s \"source /root/.profile; %s\""%(sshpass, remote_Station, yrouter)
	#run_yrouter = subprocess.Popen(remote_run, shell=True,preexec_fn=os.setpgrp)
	#os.system(remote_run)

def kill_yrouter(top_num, StationIP):
	kill_command = "%s ssh root@%s \"/root/bin/kill_yrouter %d\"" %(sshpass, StationIP, top_num)
	print kill_command
	os.system(kill_command)

def delete_wlan_iface(top_num, StationIP):
	del_command = "%s ssh root@%s \"/root/bin/del_iface t%d\"" %(sshpass, StationIP, top_num)
	print del_command
	os.system(del_command)
