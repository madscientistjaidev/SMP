# David L. Flanagan, Mike Wilson, Jugal Lodaya, Jaidev Ramakrishna
# June 30, 2016
# CRCCalculator.py
# This module calculates the IEEE-32-bit CRC using the standard aglorithm.
# it is used to ensure data integrity of messages.

import ctypes

class CRCCalculator(object):
    """Object for calculating IEEE-32-bit CRCs using the standard polynomial 0xedb88320."""

    # This is the actual look up table.
    CRCTable = []

    def __init__(self):
        """Public constructor builds the CRC table and sets up the polynomials."""
        # make these calls to build the underlying type once since we have to use them a bunch.
        self.Polynomial = ctypes.c_uint32(0xedb88320).value
        self.MinusOneUint32 = ctypes.c_uint32(0xFFFFFFFF).value

        # actually make the call to build the table.
        self.BuildCRCTable()


    def BuildCRCTable(self):
        """Builds the CRC table.  This function should not be called by the user."""

        # actually build the table from the polynomial.
        for n in range(256):
            # has to be a uint32.
            c = ctypes.c_uint32(n).value
            for k in range(8):
                if(c & 1):
                    c = self.Polynomial ^ (c >> 1)
                else:
                    c = (c >> 1)
        
            self.CRCTable.append(ctypes.c_uint32(c).value)


    def CalculateCRC(self, data):
        """This function actually calcualtes the CRC32 from some data.  Whatever you pass you should
           convert to a string or an array of bytes."""

        c = self.MinusOneUint32
        raw_bytes = bytearray(data)

        for n in range(len(raw_bytes)):
            c = ctypes.c_uint32(self.CRCTable[(c ^ raw_bytes[n]) & 0xFF] ^ (c >> 8)).value

        return c ^ self.MinusOneUint32