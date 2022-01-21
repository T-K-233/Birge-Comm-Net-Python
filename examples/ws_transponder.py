import socket
import threading
import json
import time
import hashlib
import base64
import struct
import logging

from birge_comm_net import CommNetNode

class WebsocketHandler:
    def __init__(self, conn):
        # initialize header elements
        self.method = ""
        self.uri = ""
        self.http_version = ""
        self.headers = {}
        self.content = ""
        
        self._conn = conn

    def parseHTTPRequest(self, buffer=b""):
        if not buffer:
            buffer = self._conn.recv(1024)
        
        content_splitter = buffer.find(b"\r\n\r\n")
        self.content = buffer[content_splitter:]

        buffer = buffer.decode()
        buffer_splited = buffer.split("\r\n")

        self.method, self.uri, self.http_version = buffer_splited[0].split(" ")

        self.headers = {}
        for entry in buffer_splited[1:]:
            splitter = entry.find(":");
            key = entry[:splitter]
            val = entry[splitter+1:].lstrip()
            self.headers[key] = val

    def getKeyHash(self):
        #id = "dGhlIHNhbXBsZSBub25jZQ=="
        guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            return None

        key = key + guid
        digest = hashlib.sha1(key.encode()).digest()

        key = base64.b64encode(digest)

        return key
        
    def upgradeHTTPRequest(self, buffer=b""):
        # extract request elements from raw byte buffer
        self.parseHTTPRequest(buffer)

        key = self.getKeyHash()
        if not key:
            return False
   
        response = b"HTTP/1.1 101 Switching Protocols\r\n" +\
                b"Connection: Upgrade\r\n" +\
                b"Upgrade: websocket\r\n" +\
                b"Sec-WebSocket-Accept: " + key + b"\r\n\r\n"

        # switch protocol
        self._conn.send(response)

        return True
    
    def receive(self):
        frame_header, = struct.unpack(">B", self._conn.recv(1))
        fin = (frame_header >> 7) & 0b1
        opcode = (frame_header >> 0) & 0b1111
        
        frame_header, = struct.unpack(">B", self._conn.recv(1))
        mask = (frame_header >> 7) & 0b1

        # Decoding Payload Length
        # read bits[9:15] as uint
        payload_len = (frame_header >> 0) & 0x7F

        if payload_len <= 125:
            # done
            pass
        elif payload_len == 126:
            # step 2, read next 16 bits as uint
            payload_len, = struct.unpack(">H", self._conn.recv(2))
        elif payload_len == 127:
            # step 3, read next 64 bits as uint
            payload_len, = struct.unpack(">H", self._conn.recv(8))
            
            

        #print(fin, opcode, mask, payload_len)
        # Reading and Unmasking the Data
        
        if not mask:
            # server must disconnect from a client if that client sends an unmasked message
            print("not encoded")
            self._conn.close()
            return

        masking_key = self._conn.recv(4)

        raw_content = self._conn.recv(payload_len)

        content = b""
        for i in range(payload_len):
            content += struct.pack(">B", raw_content[i] ^ masking_key[i % 4])

        return content

    def transmit(self, buffer):
        fin = 1
        opcode = 1

        extended_payload_len = 0
        if len(buffer) <= 125:
            payload_len = len(buffer)
        elif len(buffer) <= 65535:
            payload_len = 126
            extended_payload_len = struct.pack(">H", len(buffer))
        elif len(buffer) <= 0xFFFFFFFF:
            payload_len = 127
            extended_payload_len = struct.pack(">Q", len(buffer))

        frame_header = struct.pack(">BB", (fin << 7) | opcode, payload_len)
        self._conn.send(frame_header)
        if extended_payload_len != 0:
            self._conn.send(extended_payload_len)
        self._conn.send(buffer)




if __name__ == "__main__":
    key = "/sensor_node_0/temperature"
    val = -100
    client = CommNetNode()
    client.connect(("localhost", 8000))

    _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _s.bind(("localhost", 8008))
    _s.listen(1)
    #_s.settimeout(2)
    _s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)


    while True:
        try:
            conn, addr = _s.accept()
            print("accept ws connection")
            
            handler = WebsocketHandler(conn)
            
            print("upgrade ws connection")
            handler.upgradeHTTPRequest()

            print("fin")

            while True:
                buf = handler.receive()
                #print(buf)
                data = client.getAll()
                try:
                    handler.transmit(json.dumps(data).encode())
                except ConnectionAbortedError:
                    conn.close()
                    break
                #time.sleep(0.)
        except KeyboardInterrupt:
            break
        
