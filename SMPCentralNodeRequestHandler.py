# David L. Flanagan, Mike Wilson, Jugal Lodaya, Jaidev Ramakrishna
# May 14, 2016
# SMPCentralNodeRequestHandler.py
# This file pretty much is the server, it handles all the requests it handles all of the data.

from Publisher import Publisher
from Subscriber import Subscriber
from SocketServer import BaseRequestHandler 
from Command import Command
import threading
import Utility

# Count before we boot a publsiher off the network.
TIMEOUT_LIMIT = 10

# Global data.
Pubs = dict()
Transactions = dict()
TransactionID = 0

def StoreTransaction(id, command, socket, address):
    """This function logs a transaction with the central node, since it may need to be resent. """
    print "New transaction logged: ID=" + str(id) + " Address=" + str(address)
    # we store the actually command, the socket of hte client it went to, the lcients address and a timeout counter in a tuple.

    Transactions[id] = (command, socket, address, 0)


def HandleTimeout():
    """This function is called if nothing is recieved during a call to handle_request() on the UDP server."""
    
    # Keep a list of those transactions we need to remove.
    toberemoved = []

    # for all transactions...
    for key,value in Transactions.items():

        # stored the command in the zeroeth element of the tuple.
        command = Transactions[key][0]
        # stored the socket in the first element.
        socket = Transactions[key][1]
        # stored the address in the second element.
        address = Transactions[key][2]

        # RQ 14
        # the final elemnt of the transaction is the count.  If this is the second time we were here instead of
        # retrying the send we call it a loss and delete the transaction.
        if Transactions[key][3] <= 1:
            print "Resending transaction " + str(key)
            socket.sendto(command.GetPacket(), address)

            # We have to update the tuble this way since tuples are immutable.
            Transactions[key] = (Transactions[key][0], Transactions[key][1], Transactions[key][2], Transactions[key][3]+1) 
        else:
            # We are giving up on this transaction its time to remove it.
            toberemoved.append(key)

    # We have to go back and delete all of the items that we didn't retry now.
    for key in toberemoved:
        print "Transaction " + str(key) + " timed out.  Removing it."
        del Transactions[key]


    # Keep track of publishers we need to delete.
    already_incremented_subs = []
    pubs_to_be_deleted = []

    # RQ 16b
    # We also need to handle when a  subscriber doesn't send us a keep alive packet.
    for pubkey, pubvalue in Pubs.items():
        pubvalue.TimeoutCount = pubvalue.TimeoutCount + 1

        # if we have timed out we need to send a pub removed to all subsribers.
        if(pubvalue.TimeoutCount > TIMEOUT_LIMIT):
            print "Publisher " + pubkey + " has timed out.  Removing subscribers..."
            for subkey, subvalue in pubvalue.Subs.items():
                subvalue.SendCommand(Command.PUBLISHER_REMOVED, pubvalue.Key)

            # we actually have to delete the publisher, but we can't do it in the loop so we add it to a to be deleted list.
            pubs_to_be_deleted.append(pubkey)

        else: # Else the thing is okay, so now we add TimeoutCounts to the subscribers.
            subs_to_be_deleted = []

            prev_sub_count = len(pubvalue.Subs)

            for subkey, subvalue in pubvalue.Subs.items():
                # We have to make sure we have't already incrememnted this sub, since he might be on multiple publishers.
                if subkey not in already_incremented_subs:
                    subvalue.TimeoutCount = subvalue.TimeoutCount + 1
                    already_incremented_subs.append(subkey)

                    # now we need to check if the subscriber has timed out if so we delete him.
                    if subvalue.TimeoutCount > TIMEOUT_LIMIT:
                        print "Subscriber " + subkey[0] + ":" + str(subkey[1])  + " has timed out."
                        # we need to remove this subscriber, but can't do it in the loop so we add it to a list to be here.
                        subs_to_be_deleted.append(subkey)

            # now we actually remove all of the subscribers who have timed out.
            for sub in subs_to_be_deleted:
                del pubvalue.Subs[sub]

            # if that was the last subscriber we send the stop publshing command.
            if len(pubvalue.Subs) == 0 and prev_sub_count != 0:
                print "Publisher " + pubkey + " no longer has any subscribers. Sending StopPublishing..."
                pubvalue.SendCommand(Command.STOP_PUBLISHING)

    # actually do the removal of stale publishers.
    for pub in pubs_to_be_deleted:
        del Pubs[pub]


# RQ 11
def GetNextTransactionID():
    """THis function generates a negative transaction ID.  All transaction ids that come from the central
       node must have a negative number."""
    global TransactionID

    # Wrap the ID around.
    if TransactionID <= -32767:
        TransactionID = 0

    # Decrement it.
    TransactionID = TransactionID - 1

    return TransactionID

# These globals are used to keep track of available ports on the publisher network.
FirstTime = True
AvailablePorts = []

class SMPCentralNodeRequestHandler (BaseRequestHandler):
    """This class is pretty much the whole server.  It does all the respose handling and all of the
       data manipulation."""

    def FirstTimePortSetup(self):
        """We create a list of all possible ports we can use.  We do this os we can add or remove them."""
        # RQ 5
        for i in range(15002, 15555):
            AvailablePorts.append(i);


    def GetNextPort(self):
        """ Returns the next port in the list.  Also creates the new list if this is the first time this is called."""
        global FirstTime


        # Only set up the dictionary once.
        if(FirstTime):
            self.FirstTimePortSetup()
            FirstTime = False

        # Make sure a port is available before trying to add one.
        if(len(AvailablePorts) > 0):
            return AvailablePorts.pop(0)

        return None


    def handle(self):
        """This is the main function of the server.  It is called by the UDPServer whenever we recieve a request."""

        data = self.request[0].strip()
        #print "\nRecieved packet: " + Utility.PrintStringAsHex(data)

        # RQ 10
        # all command packets should be in this range, if not i throw it out.
        if len(data) < 13  or len(data) > 44:
            return

        command = Command()

        try:
            command.CreateFromPacket(data)
        except:
            print "The client sent us a bad packet, returning generic failure message..."
            packet = command.CreateFromParams(Command.FAILURE, GetNextTransactionID(), 0, Command.INVALID_COMMAND).GetPacket()
            self.request[1].sendto(packet, self.client_address)
            return

        # RQ 9
        # RQ 13
        if not command.IsCRCOkay:
            print "We received a command, but the CRC is incorrect"
            packet = command.CreateFromParams(Command.FAILURE, command.TransactionID, command.SensorType, Command.CRC_CHECK_FAILURE).GetPacket()
            self.request[1].sendto(packet, self.client_address)
            return

        # Otherwise hte packet seems to be okay so handle the command.
        if command.Code == Command.KEEP_ALIVE :
            return_packet = self.HandleKeepAlive(command)
        elif command.Code == Command.ADD_PUBLISHER :
            return_packet = self.HandleAddPublisher(command)
        elif command.Code == Command.REMOVE_PUBLISHER :
            return_packet = self.HandleRemovePublisher(command)
        elif command.Code == Command.ADD_SUBSCRIBER :
            return_packet = self.HandleAddSubscriber(command)
        elif command.Code == Command.REMOVE_SUBSCRIBER :
            return_packet = self.HandleRemoveSubscriber(command)
        elif command.Code == Command.SUCCESS :
            return_packet = self.HandleSuccess(command)
        elif command.Code == Command.FAILURE :
            return_packet = self.HandleFailure(command)
        else:
            return_packet = self.HandleUnknownCommand(command)

        # There is a change that at this point no packet was constructed by the server so we
        # make sure to check that one exists before trying to send it.
        if return_packet:
            self.request[1].sendto(return_packet.GetPacket(), self.client_address)

    def HandleKeepAlive(self, command):
        """This function handles the case where the client sends a keep alive message.  All clients
           must send keep alive messages or they will be booted from the mesh."""
        
        print "Keep alive was from " + str(self.client_address) + "."

        # There is no easy way to find everything so we do a brute force loop. 
        for pubkey, pubvalue in Pubs.items():
            # check to see who this message came from and reset all of the counts.
            if pubvalue.ClientAddress == self.client_address:
                pubvalue.TimeoutCount = 0

            for subkey, subvalue in pubvalue.Subs.items():
                # the subvalue's key is actually the client address.
                if subvalue.Key == self.client_address:
                    subvalue.TimeoutCount = 0


    def HandleAddPublisher(self, command):
        """This function handles the case where the client wishes to add a publisher to the sensor mesh"""

        print "Handling Add Publisher..."

        # The client screwed up the packet do nothing, return failure.
        if not command.Payload or command.Payload == "":
            print "Client tried to add a publisher, but did not provide an identifier."
            return Command().CreateFromParams(Command.FAILURE, command.TransactionID, 0, Command.INVALID_COMMAND)

        # RQ 15b
        # If the publisher already exists in the network.
        if Pubs.has_key(command.Payload):
            print "Client " + str(self.client_address) + " tried to add publisher that already exists."
            return Command().CreateFromParams(Command.FAILURE, command.TransactionID, 0, Command.PUB_ALREADY_EXISTS)

        # Actually add the publisher to the dictionary.
        Pubs[command.Payload] = Publisher(command.Payload, self.request, self.client_address, self.GetNextPort(), command.SensorType)
        print "Added publisher: ID=" + command.Payload + " from " + str(self.client_address)

        # RQ 15c
        # Return success.
        return Command().CreateFromParams(Command.SUCCESS, command.TransactionID, 0, Pubs[command.Payload].BroadcastPort)


    def HandleRemovePublisher(self, command):
        """This function handles the case where a client wants to remove a publisher from the mesh."""

        print "Handling RemovePubslisher..."

        # RQ 16d
        # The client screwed up the packet do nothing, return failure.
        if (not command.Payload or command.Payload == "") or (not Pubs.has_key(command.Payload)):
            print "Client " + str(self.client_address) + " tried to remove a publisher, but the identifier did not exist."
            return Command().CreateFromParams(Command.FAILURE, command.TransactionID, 0, Command.PUB_DOES_NOT_EXIST)

        # RQ 16e
        # At this point we know we have the publisher so we need to check if the person trying to remove it actually owns it.
        if Pubs[command.Payload].ClientAddress != self.client_address:
            print "Client " + str(self.client_address) + " tried to remove a publisher owned by " + str(Pubs[command.Payload].ClientAddress) + "."

            # We don't think this client owns this publisher so we return permission error.
            return Command().CreateFromParams(Command.FAILURE, command.TransactionID, 0, Command.PERMISSION_ERROR)

        # RQ 16b
        # RQ 21a
        # RQ 21b
        #finally we know that we can remove the publisher, but first we need to send a pub removed command to all of his subscribers
        for subscriber in Pubs[command.Payload].Subs:
            # this is a screwy lookup, the subscriber ends up actually being the key into our directory.
            # we have to pass the name of the publisher "command.Payload" since the subscriber doesn't store a reference to
            # the name of his publisher.
            Pubs[command.Payload].Subs[subscriber].SendCommand(Command.PUBLISHER_REMOVED, command.Payload)
            
        #actually delete the publisher
        del Pubs[command.Payload]

        #Return success.
        print "Removed publisher " + command.Payload + "."

        return Command().CreateFromParams(Command.SUCCESS, command.TransactionID, 0, self.client_address[1])


    def HandleAddSubscriber(self, command):
        """This function handles the case where the client wants to add a subscriber to the network"""
        print "Handling Add Subscriber..."

        # modifying global shared data so we need to protect this part.
        # check if the requested publisher exists
        if Pubs.has_key(command.Payload):

            publisher = Pubs[command.Payload]

            # if this is the first subscriber for this publisher then send the start publishing command to the publisher
            if 0 == len(publisher.Subs):
                # RQ 19a
                # RQ 19b
                publisher.SendCommand(Command.START_PUBLISHING)

            # add the subscriber to the publishers dictionary
            publisher.Subs[self.client_address] = Subscriber(self.request, self.client_address)

            print "Client " + self.GetClientString() + " added subscriber to publisher=" + command.Payload + "."

            # RQ 17c
            # RQ 17d
            # RQ 17f
            # build the success packet with the port number for the subscriber
            return Command().CreateFromParams(Command.SUCCESS, command.TransactionID, 0, publisher.BroadcastPort)

        else:
            print "Client " + self.GetClientString() + " tried to add a subscriber to " \
                  + command.Payload + " which does not exist"

            # RQ 17e
            # return the failure packet
            return Command().CreateFromParams(Command.FAILURE, command.TransactionID, 0, Command.PUB_DOES_NOT_EXIST)

    def HandleRemoveSubscriber(self, command):
        """This function handles the case where we recieve a remove subscriber from the client."""

        rv = None

        print "Handling Remove Subscriber..."

        # check if the requested publisher exists
        if not Pubs.has_key(command.Payload):
            # If it doesn't we send out a you are a naughty subscriber.
            return Command().CreateFromParams(Command.FAILURE, command.TransactionID, 0, Command.PUB_DOES_NOT_EXIST)

        # Get the publisher.
        publisher = Pubs[command.Payload]

        # RQ 18c
        # If this client actually owns a subscriber in this publisher...
        if publisher.Subs.has_key(self.client_address):

            print "Client " + self.GetClientString() + " removed subscriber from publisher=" + command.Payload + "."

            # remove the subscriber from the publishers dictionary
            del publisher.Subs[self.client_address]

            if len(publisher.Subs) <= 0:
                # RQ 20a
                # RQ 20b
                publisher.SendCommand(Command.STOP_PUBLISHING)

            # return the success packet
            return Command().CreateFromParams(Command.SUCCESS, command.TransactionID, 0, publisher.BroadcastPort)

        else:

            print "Client " + self.GetClientString() + " either tried to remove a subscriber from " + command.Payload + " which did not exist" + \
                  " or he was not subscribed to it."

            # RQ 18d
            # build the failure packet
            return Command().CreateFromParams(Command.FAILURE, command.TransactionID, 0, Command.PUB_DOES_NOT_EXIST)



    def HandleSuccess(self, command):
        """This function handles the case where the client responds to one of our messages with success.  The
            only thing we really need to do here is to remove the packet from the transaction queue."""

        print "Handling Success..."

        rv = None

        #first we check our transaction list to see if they are responding to a logged transaction.
        if Transactions.has_key(command.TransactionID):
            #if it did, we remove the transaction from the list.
            del Transactions[command.TransactionID]
        else:
            # otherwise, we send back a wtf are you talking about.
            rv = Command().CreateFromParams(Command.FAILURE, command.TransactionID, 0, Command.INVALID_COMMAND)

        return rv



    def HandleFailure(self, command):
        """THis function handles the case where the client sends us a failure.  The only time we can get a failure
           is when we sent a packet to a client.  The only reason this should happen is because the CRC was somehow
           corrupted."""

        #in the case that we got a failure, we retry the command, but we do not clear its resend count.
        print "Handling Failure..."

        if Transactions.has_key(command.TransactionID):
            # stored the command in the zeroeth element of the tuple.
            command = Transactions[command.TransactionID][0]
            # stored the socket in the first element.
            socket = Transactions[command.TransactionID][1]
            # stored the address in the second element.
            address = Transactions[command.TransactionID][2]

            # Retry the send.
            socket.sendto(command.GetPacket(), address)


    def HandleUnknownCommand(self, command):
        """This handler runs if a client sends us a bad packet."""
        print "Handling Unknown Command..."
        return Command().CreateFromParams(Command.FAILURE, command.TransactionID, 0, Command.INVALID_COMMAND)


    def GetClientString(self):
        """Returns the client address as a string."""
        return str(self.client_address)
