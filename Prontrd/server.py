#!/usr/bin/env python3

import socket
import sys
import os
import time

sock_address = '/tmp/prontrd.sock'

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

def initSocket():
    try:
        os.unlink(sock_address)
    except OSError:
        if os.path.exists(sock_address):
            raise

    sock.bind(sock_address)
    sock.listen(1)
    print('Bound to socket ', sock_address)

def closeSocket():
    sock.close()
    print('Unbound from socket ', sock_address)

def main():
    initSocket()

    while True:
        # wait for a connection
        connection, client = sock.accept()

        try:
            print('Connection from ', client, ' opened')
            while True:
                msg = connection.recv(2048).decode('utf-8')
                if msg:
                    # message received
                    print('Received message:')
                    print(msg)
                else:
                    # no message received, end of transmission
                    break
        finally:
            print('Connection from ', client, ' closed')
            connection.close()


if __name__ == "__main__":
    main()
