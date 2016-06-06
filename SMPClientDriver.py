""" The SMP Client test application.

    The SMP client processes are executed from the following
     python module:

        $>python SMPClientDriver.py <options>

        The input arguments to the SMPClientDriver.py executable are
     in one of the following formats. If no options are provided, the
     test application runs in interactive mode. It is not recommended
     that the grader run the test application in interactive mode.

        -addPub <StringID> <InputFile> [delayOption]

            The addPub command registers a publisher client with the
            SMP central node and publishes the InputFile contents as
            data over the network in a continuous loop. It is
            recommended that an integer delayOption is provided to
            force a delay in seconds between published data packets.
            The InputFile must be a valid file on the system and the
            delayOption must be an integer.

        -addSub <StringID> [OutputFile]

            The addSub command registers a subscriber client with the
            SMP central node and receives the published data. If the
            OutputFile argument is provided, the client process will
            write the received data to the output file. If no OutputFile
            argument is provided, then the subscriber will print the
            received data to the console. """

from SMPPublisherClient import SMPPublisherClient
from SMPSubscriberClient import SMPSubscriberClient
import sys
import re
import os
import thread
import threading
import signal
import socket
from Command import Command
import time
import struct

# dictionary of publishers and subscribers
Pubs = {}
Subs = {}
# dictionary of publisher threads publishing data and
# thread Event objects for signaling them to stop
PubThreads = {}
# dictionary of subscriber threads reading data and
# piping to a file, also has thread Event objects for signaling them to stop
SubThreads = {}

# publish data delay between packets
PublishDelay = 0

SMP_CENTRAL_NODE_ADDR = None
DEFAULT_SENSOR_TYPE = 0

ID = "ID"
NO_RESPONSE = "no response from central node"
COMMANDS = {}
COMMAND_PROMPT_STRING = None
COMMAND_PROMPT_MENU_ORDER = []
COMMAND_USAGE = {}


def addPub(id, sensor_type=0):
    global Pubs, SMP_CENTRAL_NODE_ADDR
    id = str(id)
    print " ".join( [ addPub.__name__, id, str(sensor_type) ] )

    try:
        sensor_type = int(sensor_type)
    except ValueError:
        print "invalid args. sensor_type must be an int"
        return True

    # create the publisher instance
    pub = SMPPublisherClient(SMP_CENTRAL_NODE_ADDR, id, int(sensor_type))

    # send the addPub command
    response = pub.addPub()

    if response is None:
        print NO_RESPONSE
    else:
        print "response: " + str(response)
        if Command.SUCCESS == response.Code:
            # add the publisher to the global dictionary
            Pubs[id] = pub

    return True


""" file is piped to the publishData function on a separate thread"""
def publishData(id, inputFile, chunkSize=1024):
    print " ".join( [ publishData.__name__, id, inputFile ] )
    id = str(id)

    if os.path.isfile(inputFile) and Pubs.has_key(id):
        # reference to the publisher object
        pub = Pubs[id]
        # reference to a new thread Event object to signal the publishing thread to stop
        event = threading.Event()
        # set the event so that the thread knows its ok to publish
        event.set()
        # add the publishPipedFile thread for the publisher with the event object to the global dictionary
        PubThreads[id] = (thread.start_new_thread(publishPipedFile, (pub, inputFile, chunkSize, event)), event)
    else:
        print "invalid arg: File(" + inputFile + ") exists ?= " + str(os.path.isfile(inputFile)) + \
              ", Publisher(" + id + ") exists ?= " + str(Pubs.has_key(id))
    return True


""" pipe the input file to the publisher publishData function.
    This function runs an infinite loop on a separate thread and
    is designed to be stopped by the rmPub or signalPub command.
    The function is best used on an input file that is constantly
    written to. """
def publishPipedFile(publisher, inputFile, chunkSize, event):
    # open file with read permission
    f = open(inputFile, 'r')
    # only if this thread is still set to publish data
    while event.isSet():
        # send the data chunk as a list
        s = f.read(chunkSize)
        if s is not None and 0 != len(s):
           publisher.publishData([s])
        if 0 == len(s):
            # EOF reached, start at the beginning of the file
            f.seek(0)

        time.sleep(PublishDelay)

    # close the input file
    f.close()


def rmPub(id):
    global Pubs, SMP_CENTRAL_NODE_ADDR
    print " ".join( [ rmPub.__name__, id ] )
    id = str(id)

    # if this publisher exists then use it, otherwise construct a new publisher
    if id in Pubs:
        publisher = Pubs[id]
    else:
        publisher = SMPPublisherClient(SMP_CENTRAL_NODE_ADDR, id, 0)

    # send removePub
    response = publisher.removePub()

    if response is not None:
        print "response: " + str(response)
        if Command.SUCCESS == response.Code and id in Pubs:
            # set the event to have the publisher thread exit if it is publishing
            if Pubs[id].IsPublishing:
                # second object in the tuple is the thread event
                PubThreads[id][1].clear()
                # block until the thread exits
                joinThread(PubThreads, id)
                # remove the publisher thread from the dictionary
                del PubThreads[id]

            # remove the publisher from the dictionary
            del Pubs[id]
    return True


def getPubData(id):
    print " ".join( [ getPubData.__name__, id ] )
    id = str(id)
    if id in Pubs:
        print Pubs[id]
    return True


def isPubRegistered(id):
    print " ".join( [ isPubRegistered.__name__, id ] )
    id = str(id)
    if id in Pubs:
        print "Publisher " + id + " isRegistered=" + str(Pubs[id].IsSMPClientRegistered)
    else:
        print "id<" + id + "> not in Pubs"
        for pub in Pubs:
            print pub
    return True


def isPublishing(id):
    print " ".join( [ isPublishing.__name__, id ] )
    id = str(id)
    if id in Pubs:
        print "Publisher " + id + " isPublishing=" + str(Pubs[id].IsSMPClientRegistered)
    else:
        print "id<" + id + "> not in Pubs"
        for pub in Pubs:
            print pub
    return True


def lsPubs():
    print lsPubs.__name__
    for x in Pubs:
        print Pubs[x]
    return True


def lsSubs():
    print lsSubs.__name__
    for x in Subs:
        print Subs[x]
    return True


def addSub(id, sensor_type=0):
    global SMP_CENTRAL_NODE_ADDR
    id = str(id)
    if type(sensor_type) is not int:
		print "invalid args. sensor_type must be an int"
		return True

    print " ".join([addSub.__name__, id, str(sensor_type)])
    sub = SMPSubscriberClient(SMP_CENTRAL_NODE_ADDR, id, int(sensor_type))
    response = sub.addSub()

    if response is None:
        print NO_RESPONSE
    else:
        print "response: " + str(response)
        if Command.SUCCESS == response.Code:
            # add the subscriber to the global dictionary
            Subs[id] = sub

    return True

def joinThread(threadDict, id):
    threadId = None
    # if the thread is not in the dictionary return
    if not id in threadDict:
        return
    else:
        threadId = threadDict[id]


    threads = threading.enumerate()
    for t in threads:
        if threadId == t.ident:
            try:
                t.join()
            # if the thread is a dummy thread just continue
            except AssertionError:
                None

def rmSub(id, sensor_type=0):
    global Subs, SMP_CENTRAL_NODE_ADDR

    print " ".join( [ rmSub.__name__, id ] )
    id = str(id)

    # if this subscriber exists...
    if id in Subs:
        subscriber = Subs[id]
    else:
        subscriber = SMPSubscriberClient(SMP_CENTRAL_NODE_ADDR, id, int(sensor_type))

    # send removeSub
    response = subscriber.rmSub()

    if response is not None:
        print "response: " + str(response)
        if Command.SUCCESS == response.Code and id in Subs:
            # set the event to have the subscriber thread exit if it is getting data
            if id in SubThreads:
                # second object in the tuple is the thread event
                SubThreads[id][1].clear()
                # block until the thread exits
                joinThread(SubThreads, id)
                # remove the subscriber thread from the dictionary
                del SubThreads[id]

            # remove the subscriber from the dictionary
            del Subs[id]
    else:
        print "Central node did not respond."

    return True


def getSubscriberData(id, outputFile=None):
    print " ".join([getSubscriberData.__name__, id])
    id = str(id)
    if id in Subs:
        # reference to the publisher object
        sub = Subs[id]
        # reference to a new thread Event object to signal the data subscribe thread to stop
        event = threading.Event()
        # set the event so that the thread knows its ok to subscribe to the data
        event.set()
        # add the subscribePipeToFile thread for the subscriber with the event object
        SubThreads[id] = (thread.start_new_thread(subscribePipeToFile, (sub, outputFile, event)), event)
    else:
        print "invalid arg: Publisher(" + id + ") exists ?= " + str(Pubs.has_key(id))
    return True


def subscribePipeToFile(subscriber, outputFile, event):
    packet = 0
    # if an output file is not provided then just print to the console
    if outputFile is None:
        f = sys.stdout
    else:
        # open file with write permission
        f = open(outputFile, 'w+')

    # only if this thread is still set to publish data
    while event.isSet():
        data = subscriber.getData()
        if data is not None:
            timeout, data = struct.unpack('>Q%ds' % (len(data) - 8), data)
            # write the data to the file
            f.write("\nPACKET[" + str(packet) + "] TIME[" + str(timeout) + "]\n" \
                    "DATA ---------------------------------------------------\n" \
						  + data + 
                       "\n---------------------------------------------------\n")
            packet = packet + 1

    # close the output file
    f.close()


def myQuit():
    # clear all event threads to exit and wait
    for t in PubThreads:
        # the second element in the tuple is the event
        PubThreads[t][1].clear()
        joinThread(PubThreads, t)

    PubThreads.clear()

    # clear all event threads to exit and wait
    for t in SubThreads:
        # the second element in the tuple is the event
        SubThreads[t][1].clear()
        joinThread(SubThreads, t)

    SubThreads.clear()

    return False


def myHelp():
    print COMMAND_PROMPT_STRING
    return True


def promptForInput():

    # get the input selection
    selection = raw_input("$>").split()

    # if the command exists
    if len(selection) > 0 and selection[0] in COMMANDS:
        command = COMMANDS[selection[0]]
        # num args, first element is the command
        numArgs = len(selection) - 1
        # verify the number of args given, last element is the number of required args
        if numArgs == command[-1] or numArgs == len(command) - 2:
            # call the function
            return command[-2](*selection[1:])
        # invalid number of args
        else:
            print "USAGE: " + COMMAND_USAGE[selection[0]]
            return True
    # command input is invalid
    else:
        print "INVALID COMMAND"
        return True


def addCommand(func, args, func_string=None):
    fname = ""
    # get the function name as a string for the dict key
    if func_string is None:
        fname = func.__name__
    else:
        fname = func_string

    # get the number of required arguments to the args list
    numReq = 0
    # optional args contain '=' and then at least one char
    for arg in args:
        if not re.match(".*=.+", arg):
            numReq = numReq + 1

    # append the function pointer to the arguments list
    args.append(func)
    # append the number of required args to the list
    args.append(numReq)
    COMMANDS[fname] = args
    # maintain a list of the menu order as commands are added
    COMMAND_PROMPT_MENU_ORDER.append(fname)
    # maintain usage strings for the command prompt menu
    COMMAND_USAGE[fname] = fname + " " + " ".join("<{}>".format(k) for k in list(args[0:-2]))


def createCommandListDict():
    addCommand(addPub, [ID, "SensorType=0"])
    addCommand(rmPub, [ID])
    addCommand(publishData, [ID, "InputFile"])
    addCommand(isPubRegistered, [ID])
    addCommand(isPublishing, [ID])
    addCommand(addSub, [ID, "SensorType=0"])
    addCommand(rmSub, [ID])
    addCommand(getSubscriberData, [ID, "OuputFile=None"])
    addCommand(lsPubs, [])
    addCommand(lsSubs, [])
    addCommand(myQuit, [], "quit")
    addCommand(myHelp, [], "help")


def createCommandPromptString():
    global COMMAND_PROMPT_STRING
    COMMAND_PROMPT_STRING = ""
    i = 1
    for command in COMMAND_PROMPT_MENU_ORDER:
        COMMAND_PROMPT_STRING = COMMAND_PROMPT_STRING + \
                                str(i) + ") " + COMMAND_USAGE[command] + "\n"
        i = i + 1

def printInvalidID(id):
    print "invalid id: " + str(id)
    print "publishers: " + str(Pubs)

def isArgsValid(args):
    global PublishDelay
    # validate the central node server ip address is provided
    if 2 > len(args):
        return False

    # validate the central node ip address
    if "localhost" != args[1]:
        try:
            socket.inet_aton(args[1])
        except socket.error:
            return False

    if 2 == len(args):
        return True

    # if optional command line args provided, validate them
    else:
        # if the command is addPub validate the inputfile
        if 5 <= len(args) <= 6 and "-addPub" == args[2] and os.path.isfile(args[4]):
            # if a delay is provided
            if 6 == len(args):
                try:
                    PublishDelay = int(args[5])
                except ValueError:
                    print "invalid delay arg: " + args[5]
                    return False

            return True
        # if the command is addSub validate the input args
        elif 4 <= len(args) <= 5 and "-addSub" == args[2]:
            return True
        else:
            return False

def processCommand(args):
    if "-addPub" == args[2]:
        # set the command line flag so that the published data is printed
        addPub(args[3])
        publishData(args[3], args[4])
        # wait on the publisher thread
        joinThread(PubThreads, args[3])
    elif "-addSub" == args[2]:
        addSub(args[3])
        outfile = None
        if 5 == len(args):
            outfile = args[4]
        getSubscriberData(args[3], outfile)
        # wait on the subscriber thread
        joinThread(SubThreads, args[3])
    else:
        print "invalid input args: " + str(args)

    # sit in an infinite loop until termination signal
    while True:
        None


def handler(signal, frame):
    myQuit()

def main(args):
    global SMP_CENTRAL_NODE_ADDR
    # register the signal handler
    signal.signal(signal.SIGINT, handler)

    if not isArgsValid(args):
        print """Usage: "SMPClientDriver.py <SERVER IP> [optional command line args]

  DESCRIPTION:  If no optional command line args are provided, then
                the SMPClientDriver will use an interactive menu.

                -addPub <ID> <InputFile> [delay]
                   Register a publisher with the central node using the input ID
                   and publish the input file. The publisher continuously sends
                   the file in an infinite loop until the program is terminated.
                   An optional argument for a delay in seconds between published data
                   packets can be provided.

                -addSub <ID> [OutputFile]
                   Register a subscriber with the central node to a publisher
                   identified using the input ID and retrieve the published data.
                   The optional OutputFile argument will send retrieved data to
                   the file, otherwise the retrieved data is printed on the console."""
        sys.exit()

    SMP_CENTRAL_NODE_ADDR = args[1]

    # create the command list dictionary using reflection
    createCommandListDict()
    # create the prompt string
    createCommandPromptString()

    print "******************************************\n" \
          "Sensor Mesh Protocol (SMP) Client Test App\n" \
          "******************************************\n" \

    # if optional args provided then simply process the command
    if 3 <= len(args):
        processCommand(args)

    # otherwise use the interactive menu system
    else:
        # print the help menu
        print COMMAND_PROMPT_STRING

        # prompt for input selection returns true except on quit
        while promptForInput():
            None

# end main


if __name__ == "__main__":
    main(sys.argv)
