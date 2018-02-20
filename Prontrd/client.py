#!/usr/bin/env python3

# Copyright 2018 Andrew Cassidy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
import sys
import os
import time
import json

sock_address = '/tmp/prontrd.sock'

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

sock.connect(sock_address)
payload = {
    'command': 'write',
    'property': 'printerState',
    'value': 3
}
sock.send(json.dumps(payload).encode('utf-8'))
msg = sock.recv(2048).decode('utf-8')
print(msg)
sock.close()
