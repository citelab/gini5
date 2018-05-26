from Router import *

##
# Class: the firewall device. Not fully implemented yet
class Firewall(Router):
    device_type="Firewall"

    def __init__(self):
        Device.__init__(self)

        self.num_interface=0
        self.interface=[]
        self.con_int={}
        self.next_interface_number=0

        #create two interface when the router create
        self.add_interface()
        self.add_interface()
