from .Switch import Switch

class OVSwitch(Switch):
    """
    Class definition for Open Virtual Switch devices
    """
    device_type = "OVSwitch"

    def __init__(self):
        super(OVSwitch, self).__init__()
        self.setProperty("OVS mode", "True")
