
# Sensor Mesh Protocol

Created as part of the graduate-level Computer Networks course at Drexel University by  -

 - Mike Wilson					mnw34@drexel.edu
 - Jugal Lodaya					jjl354@drexel.edu
 - David Flanagan				d.l.flanagan01@gmail.com  
 - Jaidev Ramakrishna		jr999@drexel.edu

This protocol is intended as a lightweight UDP based protocol for streaming sensor data, and for IOT networks. The essential idea behind it is the separation of the control and data communications into separate planes with different topologies.

We tested our protocol by developing a console application with a menu so we could send all of the individual commands and make sure the DFA was working correctly. This test application for the SMP protocol requires the Python 2.7 interpreter to run. It was tested in interactive mode on a network which is configured for IP Multicast. The SMP protocol test application uses clients with Multicast group IP 224.3.29.71.

The IP address for the central node to bind to must be provided on the command line. The SMP central node process binds to port 15001 as described in the protocol document. The SMP central node process is executed from the following python module: 

    $>python CentralNode.py

The SMP client processes are executed from the following python module:

    $>python SMPClientDriver.py <Server IP> <options>
The input arguments to the SMPClientDriver executable are in one of the following formats. If no options are provided, the test application runs in interactive mode. It is not recommended that the grader run the test application in interactive mode.

    -addPub <StringID> <InputFile> [delayOption]
The addPub command registers a publisher client with the SMP central node and publishes the InputFile contents as data over the network in a continuous loop. It is recommended that an integer delayOption is provided to force a delay in seconds between published data packets. The InputFile must be a valid file on the system and the delayOption must be an integer.
        
    -addSub <StringID> [OutputFile]
 The addSub command registers a subscriber client with the SMP central node and receives the published data. If the OutputFile argument is provided, the client process will write the received data to the output file. If no OutputFile argument is provided, then the subscriber will print the received data to the console.

 ***You can only have one subscriber per publisher per node/machine
 
It is possible that spamming the server or client with random packetrs of size 13-44 bytes could cause some problems.  We attempted to mitigiate this by performing a CRC check on all of the data and control packets.
