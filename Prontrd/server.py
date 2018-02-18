#!/usr/bin/env python3

import socket
import select
import queue
import sys
import os
import time

server_address = '/tmp/prontrd.sock'


server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

connections = [] # currently open connections
queues = {} # output queues to sockets



# initialize the socket
def initSocket():
    try:
        os.unlink(server_address)
    except OSError:
        if os.path.exists(server_address):
            raise

    server.bind(server_address)
    server.listen(1)
    print('Bound to socket ', server_address)

# close the socket
def closeSocket():
    server.close()
    print('Unbound from socket ', server_address)

# handle a request


# main loop
def main():
    initSocket()

    while True:

        time.sleep(.1)
        print('waiting...')
        # poll for a new connection
        readable, writable, errored = select.select([ server ], [], [], 0)

        for s in readable:
            if s is server: # a new connection from a client
                # accept connection
                connection, client = server.accept()
                print('Connection from ', client, ' opened')
                connection.setblocking(0)

                # Add connection to input socket list
                connections.append(connection)

                # Give the connection a queue for data we want to send
                queues[connection] = queue.Queue()


        if(connections):
            # poll for incoming data
            readable, writable, errored = select.select(connections,connections,connections,0)

            # handle reading data
            for s in readable:
                # read data from connection
                msg = s.recv(2048).decode('utf-8')
                if msg:
                    # message received
                    print('Received message:')
                    print(msg)
                else:
                    # no message received, end of transmission
                    print('Connection from ', client, ' closed')
                    connections.remove(s)
                    s.close()

            # handle writing data
            for s in writable:
                # write data, if present in queue
                if (not queues[s].empty):
                    msg = queues[s].get_nowait()
                    s.send(msg);

            # handle connection errors
            for s in errored:
                # close connection if an error has occured
                print('socket connection error on ', s.getpeername(), file=sys.stderr)
                connections.remove(s)
                s.close()


if __name__ == "__main__":
    main()
