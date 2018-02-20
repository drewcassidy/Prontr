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

import json
import os
import select
import socket
import sys
import time
import threading
from enum import IntEnum
from queue import Queue

from gpiozero import LED

serverAddress = '/tmp/prontrd.sock'
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

connectionQueues = {}  # output queues to sockets

IdleColor = (0xFF, 0xFF, 0xFF)
HeatingColorCold = (0x30, 0x00, 0xFF)
HeatingColorHot = (0xFF, 0x20, 0x00)
PrintingColor = (0xDF, 0xEF, 0xFF)
CompleteColor = (0x00, 0x50, 0xFF)
CanceledColor = (0xFF, 0x00, 0x00)
ErroredColor = (0xFF, 0x00, 0x00)


class LEDState(IntEnum):
    OFF = 0
    IDLE = 1
    HEATING = 2
    PRINTING = 3
    COMPLETE = 4
    CANCELED = 5
    ERRORED = 6

stateLock = threading.Lock()
stateProperties = {
    'ledIdleColor':  {
        'hue': 0x00,
        'saturation': 0xFF,
        'brightness': 0xFF},
    'psuPower': False,
    'printerPower': False,
    'printerState': LEDState.IDLE
}


def initSocket():  # initialize the socket
    try:
        os.unlink(serverAddress)
    except OSError:
        if os.path.exists(serverAddress):
            raise

    server.bind(serverAddress)
    server.listen(1)
    print('Bound to socket ', serverAddress)


def closeSocket():  # close the socket
    server.close()
    print('Unbound from socket ', serverAddress)


def openConnection(s: socket):
    s.setblocking(0)
    connectionQueues[s] = Queue()


def closeConnection(s: socket):
    connectionQueues.pop(s, none)
    s.close()


def pollSocket():  # poll an open socket and pass its message to a handler

    # poll for a new connection
    readable, writable, errored = select.select([server], [], [], 0)

    for s in readable:
        if s is server:  # a new connection from a client
            # accept connection
            connection, client = server.accept()
            openConnection(connection)
            print('Connection opened')

    if(connections):
        # poll for incoming data, if we have any open connections
        readable, writable, errored = select.select(
            connections, connections, connections, 0)

        # handle reading data
        for s in readable:
            # read data from connection
            if s not in connections:
                print('unknown socket!', file=sys.stderr)
                s.close()
                break

            message = s.recv(2048)
            if msg:
                # message received
                decoded = json.loads(msg.decode('utf-8'))
                response = handleRequest(decoded, s)
                connectionQueues[s].add(response)

            else:
                # no message received, end of transmission
                print('Connection closed')
                closeConnection(s)

        # handle writing data
        for s in writable:
            # write data, if present in queue
            if s not in connections:
                print('unknown socket!', file=sys.stderr)
                s.close()
                break

            if connections[s].output_waiting()
                message = connections[s].outputQueue.get_nowait()
                s.send(json.dumps(message).encode('utf-8'))

        # handle connection errors
        for s in errored:
            # close connection if an error has occured
            print('socket connection error on ',
                  s.getpeername(), file=sys.stderr)
            closeConnection(s)


def handleRequest(message, sock: socket):  # handle a request
    try:
        command = message['command']

        # Read Request
        if command == 'read':
            readProperty = message['property']

            with stateLock:
                # validate Request
                if readProperty not in stateProperties:
                    return errorResponse(readProperty, command, 'unknown property')

                # return the current value of readProperty
                return valueResponse(readProperty, stateProperties[readProperty])

        # Write Request
        if command == 'write':
            writeProperty = str(message['property'])
            writeValue = message['value']

            with stateLock:
                # validate request
                if writeProperty not in stateProperties:
                    return errorResponse(writeProperty, command, 'unknown property')
                if not writeValue:
                    return errorResponse(writeProperty, command, 'no value')

                # make sure we arnt trying to turn off the power while printing
                if (writeProperty == 'psuPower' and writeValue == False and printerPower == True):
                    print('blocking attempt to disable power while printing!',
                          file=sys.stderr)
                else:
                    stateProperties[writeProperty] = writeValue

                # return the current value of writeProperty
                return valueResponse(writeProperty)

    except KeyError:
        print('invalid request from ', sock.getpeername(), file=sys.stderr)


def valueResponse(propertyName: str, propertyValue):
    return {
        'command': 'response',
        'property': propertyName,
        'value': propertyValue
    }


def errorResponse(propertyName: str, command: str= '', errorMessage: str= 'generic error'):
    print('invalid {0} request to property \"{1}\": {2}'.format(
        command, propertyName, errorMessage), file=sys.stderr)

    return {'command': 'error'}

# main loop


def main():
    ticker = 0

    initSocket()

    while True:

        time.sleep(.1)
        pollSocket()


if __name__ == "__main__":
    main()
