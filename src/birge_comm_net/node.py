import socket
import json
import time


class CommNetNode:
    def __init__(self):
        self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def connect(self, addr):
        self._s.connect(addr)

    def _receive(self):
        buffer = b""
        try:
            c = self._s.recv(1)
        except (ConnectionResetError, TimeoutError):
            return buffer

        while c != b"\n":
            buffer += c
            try:
                c = self._s.recv(1)
            except (ConnectionResetError, TimeoutError):
                return buffer

        data = json.loads(buffer.decode())

        return data
    
    def _transmit(self, method, data):
        request_msg = {"method": method, "data": data}
        buffer = json.dumps(request_msg).encode()
        buffer += b"\n"
        self._s.send(buffer)
        return True

    def set(self, key, val):
        assert "\n" not in key
        if type(val) is str:
            assert "\n" not in val

        self._transmit("SET", {key: val})
        data = self._receive()

        if data.get("method") != "ACK":
            return False
        
        return True
        
    def get(self, key):
        assert "\n" not in key

        self._transmit("GET", {key: None})
        data = self._receive()

        if data.get("method") != "RES":
            return None
        
        return data

    def getAll(self):
        self._transmit("ALL", {})
        data = self._receive()

        if data.get("method") != "RES":
            return None
        
        return data
        
