""" SMPClient base class used to send commands to the central node
    and establish the command and data connection threads. """

from Command import Command
import random
import collections
import socket
import threading
import thread


# positive transaction IDs are initialized from the client to the
# central node, 16bit number
MAX_RAND_16BIT_TRANSACTION_ID = (2 ** 8) - 1


# RQ 12
def GetTransactionId():
    return random.randint(0, MAX_RAND_16BIT_TRANSACTION_ID)


class SMPClient:

    SMP_MULTICAST_GROUP = "224.3.29.71"
    SMP_CLIENT_TYPE_PUBLISHER = 1
    SMP_CLIENT_TYPE_SUBSCRIBER = 2
    # RQ 4
    SMP_CENTRAL_NODE_PORT = 15001
    NUM_TIMEOUTS = 3
    SMP_CENTRAL_NODE_RESPONSE_TIMEOUT = 1  # 1 sec
    MAX_CENTRAL_NODE_CMD_PACKET_SIZE = 1024
    DEFAULT_DATA_QUEUE_MAX_SIZE = 4096

    """ constructor takes the Central node ip address and data queue size """
    def __init__(self, smp_central_node_address, client_type, publisher_key, sensor_type,
                 command_loop, data_loop, queue_size=DEFAULT_DATA_QUEUE_MAX_SIZE):

        # ip address for the central node
        self.SMPCentralNodeAddress = \
            (smp_central_node_address, SMPClient.SMP_CENTRAL_NODE_PORT)
        # SMP client socket for command node communication
        # bind the client socket to an available port
        # RQ 3
        self.ClientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ClientSocket.bind(('', 0))
        self.ClientSocket.settimeout(SMPClient.SMP_CENTRAL_NODE_RESPONSE_TIMEOUT)
        # set the class client type
        self.ClientType = client_type
        # DataLoop and CommandLoop locks, each lock keeps the child threads running
        # When they are released by the parent, the child threads will exit their loops
        self.CommandLoop = command_loop
        self.DataLoop = data_loop
        self.CommandLoopLock = threading.Semaphore()
        self.DataLoopLock = threading.Semaphore()
        # data queue implemented as a ring buffer for the producer and consumer
        # functions of the implementation classes this data structure is thread safe
        self.DataQueue = collections.deque(maxlen=queue_size)
        # is registered flag
        self.IsSMPClientRegistered = False
        # is data publishing flag
        self.IsPublishing = False
        # publisher key used by both publisher and subscriber clients
        self.PublisherKey = publisher_key
        # publisher sensor type
        self.PublisherSensorType = sensor_type
        # data port
        self.DataPort = None

    # RQ 15a
    """ Send the addClient request using the publisher key and sensor type.
        If the response is success, start the dataLoop and commandLoop threads
        Returns command response Command object.
        Return is None if no response received """
    def addClient(self):

        # set the command code based on the client type
        addCommandCode = None

        if SMPClient.SMP_CLIENT_TYPE_PUBLISHER == self.ClientType:
            addCommandCode = Command.ADD_PUBLISHER
        elif SMPClient.SMP_CLIENT_TYPE_SUBSCRIBER == self.ClientType:
            addCommandCode = Command.ADD_SUBSCRIBER
        else:
            raise Exception("Invalid Client Type")

        # RQ 17a
        # RQ 17b
        # send the central node the addPub command, True flag waits for response
        commandResponse = self.sendCentralNodeCommand(addCommandCode,
                                                      GetTransactionId(),
                                                      self.PublisherKey,
                                                      True)

        """ STATEFUL - Transition to the Idle or Start state """
        if commandResponse is not None and Command.SUCCESS == commandResponse.Code:
            # start the client threads
            self.processAddClientResponse(commandResponse)

        # return the command response
        return commandResponse

    """ process the addClient response from the central node
        kicks off two threads, one for data and one for sending Keep Alive
        packets to the central node and for processing central node commands """
    def processAddClientResponse(self, command_response):

        if Command.SUCCESS == command_response.Code:

            # extract the broadcast port from the command response payload
            self.BroadcastPort = int(command_response.Payload)

            # set the is registered flag for the caller API
            self.IsSMPClientRegistered = True

            # acquire the thread locks to allow the child threads to
            # run their process loops immediately
            self.DataLoopLock.acquire()
            self.CommandLoopLock.acquire()

            # set the flag to indicate if data is being published
            # based on the client type. If a publisher don't set to
            # true until start publishing, if subscriber then success
            # indicates the publisher is sending data
            if SMPClient.SMP_CLIENT_TYPE_PUBLISHER == self.ClientType:
                self.IsPublishing = False
            elif SMPClient.SMP_CLIENT_TYPE_SUBSCRIBER == self.ClientType:
                self.IsPublishing = True
            else:
                raise Exception("Invalid Client Type")

            # RQ 2
            # enter the thread loop for sending Keep Alive packets and received commands
            thread.start_new_thread(self.CommandLoop, ())

            # kick off the data thread
            thread.start_new_thread(self.DataLoop, ())

        else:
            raise Exception("call to processAddPubResponse with response code != SUCCESS")

    """ helper function to send the central node a command request. returns the response
        if the flag is True and is received before the defined timeout """
    def sendCentralNodeCommand(self, command_code, transaction_id, payload=None, receiveFlag=False):

        # if no payload is provided use the publisher key
        if payload is None:
            payload = self.PublisherKey

        # create the command PDU
        commandPDU = Command().CreateFromParams(command_code,
                                                transaction_id,
                                                self.PublisherSensorType,
                                                payload).GetPacket()

        # loop breaks
        responseTimeouts = 0
        cmdResponse = None

        # send the command to the central node
        self.ClientSocket.sendto(commandPDU, self.SMPCentralNodeAddress)

        # get the command response if the flag is set
        while receiveFlag and SMPClient.NUM_TIMEOUTS > responseTimeouts:

            try:
                # read from the socket for a response
                response = self.ClientSocket.recvfrom(SMPClient.MAX_CENTRAL_NODE_CMD_PACKET_SIZE)

                # get the command response packet and exit the loop
                if response is not None:
                    cmdResponse = Command().CreateFromPacket(response[0])
                    receiveFlag = False

            except socket.timeout:
                # timeout, increment the count
                responseTimeouts += 1
            except socket.error:
                return None

        # end while

        # return the command response, this will be None for receiveFlag False and timeouts
        return cmdResponse

    """ to string method to print the SMP client info """
    def __str__(self):
        if SMPClient.SMP_CLIENT_TYPE_PUBLISHER == self.ClientType:
            typeString = "Publisher"
        elif SMPClient.SMP_CLIENT_TYPE_SUBSCRIBER == self.ClientType:
            typeString = "Subscriber"

        return typeString + ": Key=" + self.PublisherKey + \
               " SensorType=" + str(self.PublisherSensorType) + \
               " IsRegistered=" + str(self.IsSMPClientRegistered) + \
               " IsPublishing=" + str(self.IsPublishing)

