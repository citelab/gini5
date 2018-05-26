"""The logical object of a node"""

from UI.Node import *

class Device(Node):

    def __init__(self):
        """
        Create a logical side to the node.
        """
        Node.__init__(self)
        self.connection = []
   

	
