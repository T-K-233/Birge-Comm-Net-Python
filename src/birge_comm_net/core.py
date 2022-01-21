import socket
import threading
import json
import time
import hashlib
import base64
import struct
import logging


"""
examples:

server = CommNetServer(addr=("localhost", 6000), n_connections=8)

server.run()
"""
class CommNetCore:
    def __init__(self, addr=("localhost", 8000), n_connections=8, log_level=logging.INFO):
        self.addr = addr
        self.n_connections = n_connections

        # initialize network table
        self.resetNetworkTable()
        
        self._killed = False
        
        # set up socket
        self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._s.bind(self.addr)
        self._s.listen(self.n_connections)
        self._s.settimeout(2)   # set a timeout so that main thread can respond to keyboard interrupt

        # per https://stackoverflow.com/questions/19741196/recv-function-too-slow
        self._s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # logging related        
        self._logger = logging.getLogger("CommNetCore")
        self._logger.setLevel(log_level)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s]: [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        self._logger.addHandler(handler)
        
    def resetNetworkTable(self):
        # initialize default entries, according to https://build.rath-robotics.com/controllers/control-system
        self.networktable = {
            "/time": time.time(),
            "/version": "0.1.0",
        }

    """
    read message until a newline character is received
    """
    def _recv(self, conn):
        buffer = b""
        try:
            c = conn.recv(1)
        except (ConnectionResetError, TimeoutError):
            return buffer

        while c != b"\n":
            buffer += c
            try:
                c = conn.recv(1)
            except (ConnectionResetError, TimeoutError):
                return buffer

        return buffer
        
    def _send(self, conn, data):
        buffer = json.dumps(data).encode()
        buffer += b"\n"
        
        try:
            conn.send(buffer)
        except ConnectionResetError:
            return False
        
    def _processRequest(self, data):
        if not data.get("method"):
            self._logger.warning("Missing \"method\" in request.")
            return {"method": "ERR", "data": {}, "msg": "Missing \"method\" in request."}
                
        if data.get("method").upper() == "GET":
            res_data = {"method": "RES", "data": {}}
            for key in data["data"].keys():
                self._logger.debug("GET request: {key}.".format(key=key))
                
                # all path should be absolute path
                if key[0] != "/":
                    key = "/" + key
                
                val = self.networktable.get(key)
                res_data["data"][key] = val

            return res_data
                
        if data.get("method").upper() == "KEY":
            res_data = {"method": "RES", "data": {}}
            for key in self.networktable.keys():
                res_data["data"][key] = None
            
            self._logger.debug("KEY request.")

            return res_data
            
        if data.get("method").upper() == "ALL":
            res_data = {"method": "RES", "data": self.networktable}
            
            self._logger.debug("ALL request.")

            return res_data
                    
        if data.get("method").upper() == "SET":
            for key in data["data"].keys():
                val = data["data"].get(key)

                self._logger.debug("SET request: {key}->{val}.".format(key=key, val=val))
                
                if val == None:
                    self._logger.warning("val is \"None\" in SET request.")
                    
                # all path should be absolute path
                if key[0] != "/":
                    key = "/" + key

                self.networktable[key] = val
                
            return {"method": "ACK", "data": {}}

        self._logger.warning("Unknown method {method}.".format(method=data.get("method")))            
        return {"method": "ERR", "data": {}, "msg": "Unknown method {method}.".format(method=data.get("method"))}

    def _handleConnection(self, conn, addr):
        # each connection has a 5 minute timeout
        conn.settimeout(300)
        
        while not self._killed:
            # recieve first byte sequence from conn
            buffer = self._recv(conn)

            if not buffer:
                self._logger.warning("Recv timeout. Closing connection...")
                conn.close()
                return

            # lazy-update networktable upon every request
            self.networktable["/time"] = time.time()
            
            # try convert data to JSON
            data = buffer.decode()
            try:
                data = json.loads(data)
                
            except json.decoder.JSONDecodeError:
                self._logger.info("JSON decode failed.")
                continue
            
            res_data = self._processRequest(data)

            # reply with response data
            self._send(conn, res_data)
                
            # continue to process further requests within a connection
            # this will save for the overhead of establishing socket conn
        

    def run(self):
        self._logger.info("Server started.")
        while True:
            try:
                try:
                    conn, addr = self._s.accept()
                except socket.timeout:
                    continue

                self._logger.debug("Connection from {addr}.".format(addr=addr))
                t = threading.Thread(target=self._handleConnection, args=(conn, addr), daemon=True)
                t.start()
            except KeyboardInterrupt:
                break
        
        self._logger.info("Stopping server...")
        self._killed = True


