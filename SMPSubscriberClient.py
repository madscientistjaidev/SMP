""" The SMPSubscriberClient uses a command thread and data subscribing thread
    if the addSub response from the central node is success.
    The API provides an interface to retrieve data received from the publisher.
    The caller should use the constructor to initialize the subscriber, call the
    addSub command to register with the central node, then use the IsPublishing
    variable to determine if the retrieveData function should be called. The
    retrieveData function can optionally be a blocking call until data arrives
    at the subscriber node within a given timeout.
"""

import SMPClient
from Command import Command
import socket
import sys
import threading
import time
import struct


class SMPSubscriberClient(SMPClient.SMPClient):

    # UDP packet max size minus the time in millis, crc, and UDP header
    SMP_DATA_PACKET_MAX_LENGTH = (2 ** 16) - 8 - 4 - 8

    def __init__(self,
                 smp_central_node_address,
                 publisher_key,
                 sensor_type,
                 queue_size=SMPClient.SMPClient.DEFAULT_DATA_QUEUE_MAX_SIZE):

        # call the base class constructor passing in the data loop and command loop
        SMPClient.SMPClient.__init__(self,
                                     smp_central_node_address,
                                     SMPClient.SMPClient.SMP_CLIENT_TYPE_SUBSCRIBER,
                                     publisher_key,
                                     sensor_type,
                                     self.commandLoop,
                                     self.dataSubcriberLoop,
                                     queue_size)

        # stack info for thread exceptions
        self.exc_info = None
        # semaphore for the command loop to force the data loop to exit
        self.PubRemovedLock = threading.Semaphore()
        # thread event to signal the data loop to begin, after the command loop has
        # acquired the PubRemovedLock
        self.StartDataLoopEvent = threading.Event()
        # removeSub event flag for allowing the parent thread to use the command socket
        self.RemoveSubEvent = threading.Event()

    """ addSub command sent to the SMP central node server.
        If the central node returns success, then kick off the command loop and
        the data subscription loop. """
    def addSub(self):
        return self.addClient()

    """ remove subscriber """
    def rmSub(self):

        # set the event flag so that this thread has full access to the command socket
        self.RemoveSubEvent.set()

        # 200ms delay for the command loop thread to finish any socket calls
        time.sleep(0.2)

        # RQ 18a
        # RQ 18b
        # send the central node the removePub command, True flag waits for response
        commandResponse = self.sendCentralNodeCommand(Command.REMOVE_SUBSCRIBER,
                                                      SMPClient.GetTransactionId(),
                                                      self.PublisherKey,
                                                      True)

        # if the removePub command was successful release the child loop locks so
        # they can exit and clear the removePubEvent flag
        if commandResponse is not None and Command.SUCCESS == commandResponse.Code:
            # release the thread locks so that the child threads exit the loops
            self.CommandLoopLock.release()
            self.DataLoopLock.release()
            self.IsSMPClientRegistered = False
            self.IsPublishing = False

        # clear the flag so that the command loop can use the socket
        self.RemoveSubEvent.clear()

	return commandResponse


    """ return data from the data queue """
    def getData(self):
        try:
            return self.DataQueue.popleft()
        except IndexError:
            # normal to have an empty data queue, return None to the caller
            return None

    def commandLoop(self):

        # immediately acquire the pubRemovedLock so that the data loop can run
        self.PubRemovedLock.acquire()
        # set the thread event for the data loop to run
        self.StartDataLoopEvent.set()

        # build the Keep Alive packet for reuse
        keepAlive = Command().CreateFromParams(Command.KEEP_ALIVE,
                                               0,
                                               self.PublisherSensorType,
                                               " ").GetPacket()

        # non-blocking semaphore returns true if acquired
        # parent thread will release the lock if the caller uses the removePub API
        """ STATEFUL - Subscriber Listening State """
        while self.IsPublishing and not self.CommandLoopLock.acquire(False):

            time.sleep(5)

            try:

                # if the removeSub flag is set, then continue looping
                # because the parent thread is using the command socket
                if self.RemoveSubEvent.isSet():
                    time.sleep(0.2) # 200 ms delay
                    continue

                # check for commands from the central node for pub removed
                command = self.ClientSocket.recvfrom(SMPClient.SMPClient.MAX_CENTRAL_NODE_CMD_PACKET_SIZE)

                # get the SMP command from the response packet
                cmdResponse = Command().CreateFromPacket(command[0])

                # RQ 16c
                # RQ 21c
                # check for publisher removed command
                """ STATEFUL - Transition to the Finished State """
                if Command.PUBLISHER_REMOVED == cmdResponse.Code:
                    # respond to the central node with success command
                    self.sendCentralNodeCommand(Command.SUCCESS, cmdResponse.TransactionID, 0)
                    # release the pub removed lock to force the data loop to exit
                    self.PubRemovedLock.release()
                    self.IsPublishing = False
                    self.IsSMPClientRegistered = False

                # not a publisher removed command
                else:
                    self.sendCentralNodeCommand(Command.FAILURE, cmdResponse.TransactionID, Command.INVALID_COMMAND)

            except socket.timeout:
                # socket timeouts are normal, no commands received from the command node
                None
            except Exception:
                # save off the exception in a class variable for the caller
                self.exc_info = "sub command loop " + str(self) + " " + str(sys.exc_info())

            # RQ 7
            # send the Keep Alive Packet to the central node
            self.ClientSocket.sendto(keepAlive, self.SMPCentralNodeAddress)

        # end while

    """ Enter the data subscriber loop. push data into the queue as it is
        received from the published broadcast port. If the pub removed command
        is received, then the parent thread will release the locks to exit this
        thread. """
    def dataSubcriberLoop(self):

        # don't execute until the command loop has acquired the pubRemovedLock
        # this thread should not immediately exit
        while not self.StartDataLoopEvent.isSet():
            None

        # create a data receiving socket
        # RQ 3
        dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            dataSocket.bind(('', self.BroadcastPort))
        except:
            print "You tried to add a subscriber that already exists on this machine... Please don't do that."

        dataSocket.settimeout(1)

        #create the multicast group.
        group = socket.inet_aton(SMPClient.SMPClient.SMP_MULTICAST_GROUP)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        dataSocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # RQ 16c
        # non-blocking semaphore returns true if acquired
        # parent thread will release the lock if the caller uses the removeSub API
        # the PubRemovedLock will be released by the the command thread, when a
        # pubRemoved command is received
        """ STATEFUL - Check to remain in the Listening state or transition to Finished """
        while not self.DataLoopLock.acquire(False) and not self.PubRemovedLock.acquire(False):

            try:
                # receive data from the broadcast port and put it in the data queue
                self.DataQueue.append(
                    dataSocket.recvfrom(SMPSubscriberClient.SMP_DATA_PACKET_MAX_LENGTH)[0])

            except socket.timeout:
                # normal to have a socket timeout, no data in the socket
                None
            except (socket.error, IndexError):
                # full deque or socket error
                print "error receiving data in the subscriber loop"
            except Exception:
                print "unknown error in the subscriber data loop"
                self.exc_info = "sub data loop " + str(self) + " " + str(sys.exc_info())

        # close the data socket
        dataSocket.close()


