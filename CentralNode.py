# David L. Flanagan, Mike Wilson, Jugal Lodaya, Jaidev Ramakrishna
# May 14, 2016
# CentralNode.py
# Main entry to the central node.  Kicks off the central node server.

import SMPCentralNodeRequestHandler
from SMPCentralNodeServer import SMPCentralNodeServer
import socket

class SMPCentralNode:
    """Main entry point for the central node server.  This creates the request handler."""

    def __init__(self, ip_str, port_num):
        """ Public constructor kicks off the server. """
        self.Server = SMPCentralNodeServer(ip_str, port_num, SMPCentralNodeRequestHandler.SMPCentralNodeRequestHandler)
        self.Server.timeout = 1
        self.Server.handle_timeout = SMPCentralNodeRequestHandler.HandleTimeout

    def Start(self):
        """ Handle one request after another forever"""
        while True:
            self.Server.handle_request()


if __name__ == "__main__":

    ip_addr = socket.gethostbyname(socket.gethostname())

    print "Starting server on " + ip_addr + ":15001"

    # RQ 4
    central_node = SMPCentralNode(ip_addr, 15001)
    central_node.Start()
