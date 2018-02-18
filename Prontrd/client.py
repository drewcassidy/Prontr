#!/usr/bin/env python3

import socket
import sys
import os
import time

sock_address = '/tmp/prontrd.sock'

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

sock.connect(sock_address)
sock.send('hello!'.encode('utf-8'))
time.sleep(1)
sock.close()
