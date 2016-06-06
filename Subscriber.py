# David L. Flanagan, Mike Wilson, Jugal Lodaya, Jaidev Ramakrishna
# May 14, 2016
# Publisher.py
# Data structure representing a publisher on the central node.

from Command import Command
import SMPCentralNodeRequestHandler

class Subscriber(object):
    """Data structure representing a single subscriber in the CentralNode."""

    def __init__(self, request, client_address, sensor_type=0):
        """Public constructor sets up all important variables."""
        self.Key = client_address
        self.Socket = request[1]
        self.SensorType = sensor_type
        self.TimeoutCount = 0

    def SendCommand(self, cmd_code, pub_name):
        """Sends a command to the subscriber over the network. """

        # Get the transaction id and create the command structure.
        TxId = SMPCentralNodeRequestHandler.GetNextTransactionID()
        command = Command().CreateFromParams(cmd_code, TxId, self.SensorType, pub_name)

        #log the transaction, the Key is the client address in this case.
        SMPCentralNodeRequestHandler.StoreTransaction(TxId, command, self.Socket, self.Key)

        print "Sending: " + command.GetCommandString() + " <" + str(command) + ">"

        # In a happy accident the subscribers key is actually the client address, so we just pass that into the send call.
        self.Socket.sendto(command.GetPacket(), self.Key)