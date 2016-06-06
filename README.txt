README

  Requirements:
    Python 2.7 interpreter
    
  Description:
        This test application for the SMP protocol was tested on the 
     Drexel tux network which is configured for IP Multicast. It
     is recommended that the grader test on the tux network. 
     The network IP devices must be configured to use IP Multicast
     as the SMP protocol test application uses clients with Multicast
     group IP 224.3.29.71 . The protocol was tested using the following
     test application in interactive mode.
        
        The SMP central node process is executed from the following 
     python module: 
        
        $>python CentralNode.py
        
        The IP address for the central node to bind to must be provided
     on the command line. The SMP central node process binds to port
     15001 as described in the protocol document.
     
        The SMP client processes are executed from the following
     python module:
     
        $>python SMPClientDriver.py <Server IP> <options>
        
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
            received data to the console.

     ***You can only have one subscriber per publisher per node/machine
	 
	 Robustness:
	 
	 We tested our protocol by developing a console application with a menu so we could
	 send all of the individual commands and make sure the DFA was working correctly.  It is possible
	 that spamming the server or client with random packetrs of size 13-44 bytes could 
	 cause some problems.  We attempted to mitigiate this by performing a CRC check on all
	 of the data and control packets.  
	 
	 We did not implement the extra credit.