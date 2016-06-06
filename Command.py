# David L. Flanagan, Mike Wilson, Jugal Lodaya, Jaidev Ramakrishna
# May 14, 2016
# Command.py
# Data structure that represents a single control command PDU.

from struct import *
from CRCCalculator import CRCCalculator

class Command:
    """This class is a data structure representing a single control command PDU."""

    # RQ 6
    # All of the command codes.
    KEEP_ALIVE = 0
    ADD_PUBLISHER = 1
    REMOVE_PUBLISHER = 2
    ADD_SUBSCRIBER = 3
    REMOVE_SUBSCRIBER = 4
    SUCCESS = 5
    FAILURE = 6
    PUBLISHER_REMOVED = 7
    START_PUBLISHING = 8
    STOP_PUBLISHING = 9

    # all of the error codes.
    INVALID_COMMAND = 1
    CRC_CHECK_FAILURE = 2
    PUB_DOES_NOT_EXIST = 3
    PUB_ALREADY_EXISTS = 4
    PERMISSION_ERROR = 5

    # RQ 8
    # These strings are used to parse the different kinds of commands.
    SUCCESS_DECODER_STRING = '>BhBIII'
    FAILURE_DECODER_STRING = '>BhBIiI'
    DEFAULT_DECODER_STRING = '>BhBI%dsI'

    # all command PDUs have a header of 12 bytes.
    HEADER_LENGTH = 12

    # Create the CRC object once since it has to build a table.
    CRCCalc = CRCCalculator()

    def CreateFromParams(self, code, transaction_id, sensor_type, payload):
        """Since python doesn't provide constructor overloads this is my solution two 
           different functions that parse data into the different packet fields. This one
           happens to just store the passed paremeters"""
        self.Code = code
        self.TransactionID = transaction_id
        self.SensorType = sensor_type
        self.Payload = payload
        self.CRC = 0

        #The payload can be a string or a number, if its a number when we try to find the length
        # we will get an exception.  If we got an exception we know the length is 4.
        try:
            self.Length = len(payload)
        except:
            self.Length = 4

        # We return self for convinience not really necessary.
        return self


    def CreateFromPacket(self, packet):
        """Since python doesn't provide constructor overloads this is my solution two 
           different functions that parse data into the different packet fields. This one happens
           to generate the packet from the raw bytes."""
        # Store total length since we might need it in GetDecoderString()
        self.Length = len(packet) - self.HEADER_LENGTH

        # We need to grab the code here, so that GetDecoderString() has something to switch on.
        # python packs it as a string with '\x00' this magic is to get an int, map(ord, x) returns a list
        # of its so we take the zeroth element since we know there is only 1.
        self.Code = map(ord, packet[0])[0]

        # actually do the parsing.
        self.Code, self.TransactionID, self.Reserved, self.SensorType, self.Payload, self.CRC \
            = unpack(self.GetDecoderString(), packet)

        # check for the CRC
        if not self.IsCRCOkay():
           print "BAD CRC"
           return None

        return self


    def GetPacket(self):
        """This function packs the commands parmaters into a byte array for transmission.  It always calculates the
           CRC and stores that in the packet."""

        # We have to create hte packet without the CRC first so that we can calcuate it.
        noCrcPacket = pack(self.GetDecoderString(), self.Code, self.TransactionID, 0, self.SensorType, self.Payload, 0)
        noCrcString = noCrcPacket[0:-4]

        crc = self.CRCCalc.CalculateCRC(noCrcString)

        # create and return a new packet that now has the CRC.
        return pack(self.GetDecoderString(), self.Code, self.TransactionID, 0, self.SensorType, self.Payload, crc)


    def GetDecoderString(self):
        """ Depending on what type of command we are building or parsing it may have a different structure.
            This function returns a special parsing string used by the "struct" module of python."""
        if(self.Code == self.SUCCESS):
            return self.SUCCESS_DECODER_STRING
        elif(self.Code == self.FAILURE):
            return self.FAILURE_DECODER_STRING
        else:
            # all other types of packets use this default string.
            return self.DEFAULT_DECODER_STRING % self.Length 


    def IsCRCOkay(self):
        """Calculates the CRC of an entire packet and compares it to its stored CRC.
           Returns True if the CRC of the packet was correct or false otherwise."""
        # Get the raw bytes.
        packet = self.GetPacket()
        # Skip the last four bytes since we can't include the CRC in the packet.
        return self.CRC == CRCCalculator().CalculateCRC(packet[0:-4])


    def GetCommandString(self):
        """This function maps command codes to strings for easy printing."""
        if self.Code == self.KEEP_ALIVE:
            return "KEEP_ALIVE"
        if self.Code == self.ADD_PUBLISHER:
            return "ADD_PUBLISHER"
        if self.Code == self.REMOVE_PUBLISHER:
            return "REMOVE_PUBLISHER"
        if self.Code == self.ADD_SUBSCRIBER:
            return "ADD_SUBSCRIBER"
        if self.Code == self.REMOVE_SUBSCRIBER:
            return "REMOVE_SUBSCRIBER"
        if self.Code == self.SUCCESS:
            return "SUCCESS"
        if self.Code == self.FAILURE:
            return "FAILURE"
        if self.Code == self.PUBLISHER_REMOVED:
            return "PUBLISHER_REMOVED"
        if self.Code == self.START_PUBLISHING:
            return "START_PUBLISHING"
        if self.Code == self.STOP_PUBLISHING:
            return "STOP_PUBLISHING"


    def GetStringFromErrorCode(self, code):
        """This function maps error codes to strings for easy printing."""
        if code == self.INVALID_COMMAND:
            return "INVALID_COMMAND"
        if code == self.CRC_CHECK_FAILURE:
            return "CRC_CHECK_FAILURE"
        if code == self.PUB_DOES_NOT_EXIST:
            return "PUB_DOES_NOT_EXIST"
        if code == self.PUB_ALREADY_EXISTS:
            return "PUB_ALREADY_EXISTS"
        if code == self.PERMISSION_ERROR:
            return "PERMISSION_ERROR"


    def __str__(self):
        """Default __STR__ override.  Used to print the packet parameters to the console in a convinient manner."""
        return "Code=" + self.GetCommandString() + " TxID=" + str(self.TransactionID) + \
               " SensorType=" + str(self.SensorType) + " Payload=" + str(self.Payload) + \
               " CRC=" + str(self.CRC)
