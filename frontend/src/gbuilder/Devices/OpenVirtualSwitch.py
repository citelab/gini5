from .Switch import Switch

class OpenVirtualSwitch(Switch):
    device_type = "OpenVirtualSwitch"

    def __init__(self):
        super(OpenVirtualSwitch, self).__init__()
        self.setProperty("OVS mode", "True")
