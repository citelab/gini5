from ServerAPI import WGINI_Server


try:
	wgini_server = WGINI_Server("192.168.54.121", 60000)
	title="WGINI server"
	command= "rxvt -T \"" +title+ "\" -e " + wgini_server.StartServer() + "\""
	please_open=subprocess.Popen(str(command),shell=True,preexec_fn=os.setpgrp)
except:
	print("Unexpected error:", sys.exc_info()[0])
	raise

