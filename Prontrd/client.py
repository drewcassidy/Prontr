#!/usr/bin/env python3

import socket
import sys
import os
import time
import json

sock_address = '/tmp/prontrd.sock'

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

sock.connect(sock_address)
payload = {
    'type': 'read',
    'property': 'ledState'
}
sock.send(json.dumps(payload).encode('utf-8'))
msg = sock.recv(2048).decode('utf-8')
print(msg)
time.sleep(1)
sock.close()
