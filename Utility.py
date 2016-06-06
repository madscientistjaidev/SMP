# David L. Flanagan, Mike Wilson, Jugal Lodaya, Jaidev Ramakrishna
# May 14, 2016
# Utility.py
# A collection of utilities.

def PrintStringAsHex(s):
    """Prints a string in a raw hex format."""
    return ":".join("{:02x}".format(ord(c)) for c in s)