# David L. Flanagan, Mike Wilson, Jugal Lodaya, Jaidev Ramakrishna
# May 14, 2016
# Publisher.py
# Data structure representing a subscriber on the central node.

from Command import Command
import SMPCentralNodeRequestHandler

class Publisher(object):
    """Data structure representing a single publisher in the CentralNode."""

    def __init__(self, key, request, client_address, broadcast_port, sensor_type=0):
        """Public constructor sets up all important variables."""
        self.Subs = dict()
        self.BroadcastPort = broadcast_port
        self.Key = key
        self.Socket = request[1]
        self.ClientAddress = client_address
        self.SensorType = sensor_type
        self.TimeoutCount = 0


    def SendCommand(self, cmd_code):
        """ Sends a command to the publisher over the network. """

        # Get the id ahead of time since we need it to log the transaction.
        TxId = SMPCentralNodeRequestHandler.GetNextTransactionID()

        #Create the command the key is the payload, its the name of the publisher.
        command = Command().CreateFromParams(cmd_code, TxId, self.SensorType, self.Key)

        # We log the transaction with the central node since we may need to resend it if we don't get a success.
        SMPCentralNodeRequestHandler.StoreTransaction(TxId, command, self.Socket, self.ClientAddress)

        print "Sending: " + command.GetCommandString() + " <" + str(command) + ">"

        # Actually do the sending.
        self.Socket.sendto(command.GetPacket(), self.ClientAddress)