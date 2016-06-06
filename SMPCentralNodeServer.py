# David L. Flanagan, Mike Wilson, Jugal Lodaya, Jaidev Ramakrishna
# May 14, 2016
# SMPCentralNodeServer.py
# This class is a wrapper for the python UDP server.

from SMPCentralNodeRequestHandler import SMPCentralNodeRequestHandler
from SocketServer import ThreadingUDPServer

class SMPCentralNodeServer(ThreadingUDPServer):
    """Wrapper for pythons built in UDP server. """

   
    def __init__(self, ip_str, port_num, handler):
        """Constructor fills in the ip and port numbers, and sets up the response handler."""
        self.SMPCentralNodeServerAddress = (ip_str, port_num)
        self.Handler = handler;
        # RQ 1
        # RQ 3
        ThreadingUDPServer.__init__(self, self.SMPCentralNodeServerAddress, self.Handler)