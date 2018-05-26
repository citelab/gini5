"""The wireless version of a connection"""

from Connection import Connection

class Wireless_Connection(Connection):
    type = "Wireless_Connection"

    def __init__(self, source, dest):
        """
        Create a connection between wireless devices.
        """
        Connection.__init__(self, source, dest)
