""" Various utility functions """

import os

def progExists(prog):
    """
    Check if the given program exists in the executable path.
    Return True if program found, false otherwise
    """
    for path in os.environ["PATH"].split(os.pathsep):
        file = os.path.join(path, prog)
        if os.path.exists(file) and os.access(file, os.X_OK):
            return True
    return False
