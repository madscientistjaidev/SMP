""" The SMPPublisherClient uses a command thread and data publishing thread
    once the addPub command returns success. The user instantiates an SMPPublisherClient
    object and then calls the addPub function. If the command object returned from
    addPub has a command code of SUCCESS, the user can call the other SMP publisher
    functions. The SMPPublisherClient uses a circular queue to publish data using
    non-blocking locks to acquire the queue for producing and consuming data between
    the parent thread and data publishing thread. This is done so that the most recent
    data is always in the queue or being broadcasted from the queue. """

import SMPClient
from Command import Command
import socket
import threading
import time
import sys
from struct import *
import ctypes


class SMPPublisherClient(SMPClient.SMPClient):

    def __init__(self,
                 smp_central_node_address,
                 publisher_key,
                 sensor_type,
                 queue_size=SMPClient.SMPClient.DEFAULT_DATA_QUEUE_MAX_SIZE):

        # call the base class constructor passing in the data loop and command loop
        SMPClient.SMPClient.__init__(self,
                                     smp_central_node_address,
                                     SMPClient.SMPClient.SMP_CLIENT_TYPE_PUBLISHER,
                                     publisher_key,
                                     sensor_type,
                                     self.commandLoop,
                                     self.dataPublisherLoop,
                                     queue_size)

        # startPublishing event thread flag for the data loop to send data
        self.StartPublishingEvent = threading.Event()
        # stack info for thread exceptions
        self.exc_info = None
        # removePub flag used for the parent thread to gain control
        # of the command socket if needed
        self.RemovePubEvent = threading.Event()

    """ send the addPub command to the central node to register this publisher.
        returns the central node command response object. """
    def addPub(self):
        return self.addClient()

    # RQ 16
    """ STATEFUL - Transition to the Finished State """
    """ send the removePub command to the central node to unregister this publisher.
        returns removePub command response Command object.
        return is None if no response received """
    def removePub(self):

        # set the remove pub event so that the command loop thread does
        # not use the command socket at the same time
        self.RemovePubEvent.set()

        # 200ms delay for the command loop thread to finish any socket calls
        time.sleep(0.2)

        # send the central node the removePub command, True flag waits for response
        commandResponse = self.sendCentralNodeCommand(Command.REMOVE_PUBLISHER,
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
        self.RemovePubEvent.clear()

        # return the command response
        return commandResponse

    """ publish data over the broadcast port.
        this function only adds data to the threaded queue for the
        dataPublisherLoop to broadcast. If the start publishing command
        was not received from the central node, then the data just sits in
        the queue. The caller is advised to check the IsPublishing attribute
        to save processing on publishData. data argument must be an iterable """
    def publishData(self, data):
        for x in data:
            self.DataQueue.append(x)

    """ loop forever until the removePub command flag is set.
        in each loop iteration check the startPublishing flag
        and the removePub flag set by the commandLoop thread
    """
    def dataPublisherLoop(self):

        destAddr = (SMPClient.SMPClient.SMP_MULTICAST_GROUP, self.BroadcastPort)

        # RQ 3
        # create a broadcast socket
        dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dataSocket.bind(('', 0))
        dataSocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

        # non-blocking semaphore returns true if acquired
        # parent thread will release the lock if the caller uses the removePub API
        """ STATEFUL - Publisher Registered State """
        while not self.DataLoopLock.acquire(False):

            # check if the startPublishing flag is set
            """ STATEFUL - Determine if the publisher is in the Active or Registered state """
            if self.StartPublishingEvent.isSet():

                # send any data in the queue over the broadcast network address
                # do not continuously send data that is queued up by the parent thread
                # must periodically check the removePub
                packets = self.DataQueue.maxlen
                while packets > 0:
                    try:
                        # RQ 6
                        # create an SMP data packet with data from the deque
                        stamp = round(time.time() * 1000) # ms
                        data = self.DataQueue.popleft()
                        mystamp = ctypes.c_ulonglong(int(stamp)).value
                        packet = pack('>Q%ds' % len(data), mystamp, data)
                        dataSocket.sendto(packet, destAddr)

                        # count down because another thread may be enqueuing packets
                        # and we don't want to stay in this inner loop forever
                        packets -= 1
                    except IndexError:
                        # normal to have an error if popping an empty deque
                        None
                    except socket.error:
                        # deque is empty or socket took a None data arg
                        print "error sending data in the publisher loop"
                    except Exception:
                        print "exception " + sys.exc_info()
                        self.exc_info = "pub data loop " +  str(self) + " " + str(sys.exc_info())

        # end outer while

        # close the data socket
        dataSocket.close()

    """ loop forever until the removePub command flag is set.
        in each loop iteration send the Keep Alive packet to
        the central node and check for commands to start/stop publishing
    """
    def commandLoop(self):

        # build the Keep Alive packet for reuse
        keepAlive = Command().CreateFromParams(Command.KEEP_ALIVE,
                                               0,
                                               self.PublisherSensorType,
                                               self.PublisherKey).GetPacket()

        # non-blocking semaphore returns true if acquired
        # parent thread will release the lock if the caller uses the removePub API
        """ STATEFUL - Publisher Registered State """
        while not self.CommandLoopLock.acquire(False):

            time.sleep(5)

            try:

                # if the removePub flag is set, then continue looping
                # because the parent thread is using the command socket
                """ STATEFUL - Transition to the Finished State """
                if self.RemovePubEvent.isSet():
                    time.sleep(0.2) # 200 ms delay
                    continue

                # check for commands from the central node start/stop publishing
                command = self.ClientSocket.recvfrom(SMPClient.SMPClient.MAX_CENTRAL_NODE_CMD_PACKET_SIZE)

                # get the SMP command from the response packet
                cmdResponse = Command().CreateFromPacket(command[0])

                """ STATEFUL - Transition to Idle 2 """
                # check for start publishing command
                if Command.START_PUBLISHING == cmdResponse.Code and not self.IsPublishing:
                    # release the startPublishing lock and set the class flag
                    # this free semaphore allows the dataPublisherLoop to broadcast
                    # RQ 19c
                    """ STATEFUL - Transition to Active """
                    self.sendCentralNodeCommand(Command.SUCCESS, cmdResponse.TransactionID, 0)
                    self.StartPublishingEvent.set()
                    self.IsPublishing = True

                # check for stop publishing command
                # STATEFUL - Transition to the Registered state
                elif Command.STOP_PUBLISHING == cmdResponse.Code and self.IsPublishing:
                    # RQ 20c
                    self.sendCentralNodeCommand(Command.SUCCESS, cmdResponse.TransactionID, 0)
                    # blocking, once acquired, stops the dataPublisherLoop from broadcast
                    self.StartPublishingEvent.clear()
                    # acquire the startPublishing lock and set the class flag
                    self.IsPublishing = False

                # not a start or stop command
                else:
                    print "pub client command received not start/stop: " + cmdResponse[0]
                    # acquire the lock first so that the socket isn't being used on both threads
                    self.sendCentralNodeCommand(Command.FAILURE, cmdResponse.TransactionID, Command.INVALID_COMMAND)

            except socket.timeout:
                # socket timeouts are normal, no command received from the central node
                None
            except socket.error:
                # print "socket error in the publisher command loop"
                None
            except Exception:
                self.exc_info = "pub command loop " + str(self) + " " + str(sys.exc_info())

            # RQ 7
            # send the Keep Alive Packet to the central node
            self.ClientSocket.sendto(keepAlive, self.SMPCentralNodeAddress)

        # end while


