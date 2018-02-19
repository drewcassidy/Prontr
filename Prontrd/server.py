#!/usr/bin/env python3

import json
import os
import queue
import select
import socket
import sys
import time
from enum import IntEnum

import gpiozero

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


class PSUState(IntEnum):
    OFF = 0
    ON = 1
    ERROR = 2


class PrinterState(IntEnum):
    OFF = 0
    ON = 1
    ERROR = 2


ledState: LEDState = LEDState.IDLE
ledIdleColor: {
    'hue': 0x00,
    'saturation': 0xFF,
    'brightness': 0xFF}
psuState: PSUState = PSUState.OFF
PrinterState: PrinterState = PrinterState.OFF

publicProperties = ['ledState', 'ledIdleColor', 'psuState', 'printerState']


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


def pollSocket(callback):  # poll an open socket and pass its message to a handler

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
        if message['command'] == 'read':
            readProperty = message['property']

            print('handling read request for ', readProperty)

            if readProperty in publicProperties:
                return {
                    'type': 'response',
                    'property': readProperty,
                    'value': globals[readProperty]
                }
            else:
                print('invalid read request from property \"{}\": unknown property'.format(
                    readProperty), file='/dev/stderr')
                return {'type': 'error'}

        if message['command'] == 'write':
            writeProperty = message['property']

            print('handling write request for ', writeProperty)

            if writeProperty in publicProperties:
                newValue = message['value']
                if newValue:
                    if type(newValue) == type(globals[writeProperty]):
                        globals[writeProperty] = newValue
                    else:
                        print('invalid write request to property \"{0}\": type error\ntype {1} is not the same as type {2}'
                              .format(writeProperty, type(newValue), type(globals[writeProperty])), file='/dev/stderr')
                else:
                    print('invalid write request to property \"{}\": no value'
                          .format(writeProperty), file='/dev/stderr')
            else:
                print('invalid write request to property \"{}\": unknown property'.format(
                    writeProperty), file='/dev/stderr')

    except KeyError:
        print('invalid request from ', sock.getpeername(), file='/dev/stderr')
    finally:
        return


# main loop


def main():
    initSocket()

    while True:

        time.sleep(.1)
        pollSocket(handleRequest)


if __name__ == "__main__":
    main()
