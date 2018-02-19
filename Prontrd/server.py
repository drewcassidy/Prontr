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
import queue
import select
import socket
import sys
import time
from enum import IntEnum

from gpiozero import LED

serverAddress = '/tmp/prontrd.sock'
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

connections = []  # currently open connections
queues = {}  # output queues to sockets

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


ledState = LEDState.IDLE
ledIdleColor = {
    'hue': 0x00,
    'saturation': 0xFF,
    'brightness': 0xFF}
psuPower = false
printerPower = false

publicProperties = ['ledState', 'ledIdleColor', 'psuPower', 'printerPower']


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


def pollSocket():  # poll an open socket and pass its message to a handler

    # poll for a new connection
    readable, writable, errored = select.select([server], [], [], 0)

    for s in readable:
        if s is server:  # a new connection from a client
            # accept connection
            connection, client = server.accept()
            print('Connection opened')
            connection.setblocking(0)

            # Add connection to input socket list
            connections.append(connection)

            # Give the connection a queue for data we want to send
            queues[connection] = queue.Queue()

    if(connections):
        # poll for incoming data, if we have any open connections
        readable, writable, errored = select.select(
            connections, connections, connections, 0)

        # handle reading data
        for s in readable:
            # read data from connection
            msg = s.recv(2048)
            if msg:
                # message received
                print('Received message:')
                print(msg)
                msgDict = json.loads(msg, encoding='utf-8')

                responseDict = handleRequest(msgDict, s)
                response = json.dumps(responseDict).encode('utf-8')
                if response:
                    print(response)
                    queues[s].put(response)
            else:
                # no message received, end of transmission
                print('Connection closed')
                connections.remove(s)
                s.close()

        # handle writing data
        for s in writable:
            # write data, if present in queue
            if (not queues[s].empty()):
                msg = queues[s].get_nowait()
                s.send(msg)

        # handle connection errors
        for s in errored:
            # close connection if an error has occured
            print('socket connection error on ',
                  s.getpeername(), file=sys.stderr)
            connections.remove(s)
            s.close()


def handleRequest(message, sock: socket):  # handle a request
    try:
        command = message['command']

        # Read Request
        if command == 'read':
            print('handling read request for ', readProperty)
            readProperty = message['property']

            # validate Request
            if readProperty not in publicProperties:
                return errorResponse(command, 'unknown property')

            # return the current value of readProperty
            return valueResponse(readProperty)

        # Write Request
        if command == 'write':
            print('handling write request for ', writeProperty)
            writeProperty = message['property']
            writeValue = message['value']

            # validate request
            if writeProperty not in publicProperties:
                return errorResponse(command, 'unknown property')
            if not writeValue:
                return errorResponse(command, 'no value')
            if type(writeValue) is not type(globals[writeProperty]):
                return errorResponse(command, 'type error: type {0} is not the same as type {1}'.format(type(writeValue), type(globals[writeProperty])))

            # make sure we arnt trying to turn off the power while printing
            if (writeProperty == 'psuPower' and writeValue == false and printerPower == true):
                print('blocking attempt to disable power while printing!')
            else:
                globals[writeProperty] = newValue

            # return the current value of writeProperty
            return valueResponse(writeProperty)

    except KeyError:
        print('invalid request from ', sock.getpeername(), file='/dev/stderr')
    finally:
        return


def valueResponse(propertyName: str):
    return {
        'command': 'response',
        'property': readProperty,
        'value': globals[readProperty]
    }


def errorResponse(command: str= '', errorMessage: str= ''):
    print('invalid {0} request to property \"{1}\"'.format(
        command), file='/dev/sterr')
    if errorMessage:
        print(errorMessage, file='/dev/stderr')

    return {'command': 'error'}

# main loop


def main():
    initSocket()

    while True:

        time.sleep(.1)
        pollSocket()


if __name__ == "__main__":
    main()
