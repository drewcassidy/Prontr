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
import socket
import sys
import threading
import time
from enum import IntEnum

from gpiozero import *

serverAddress = '/tmp/prontrd.sock'
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

psu_timeout = 0.1  # seconds

IdleColor = (1.0, 1.0, 1.0)
HeatingColorCold = (0.2, 0.0, 1.0)
HeatingColorHot = (1.0, 0.2, 1.0)
PrintingColor = (0.7, 0.8, 1.0)
CompleteColor = (0.0, 0.4, 1.0)
CanceledColor = (1.0, 0.0, 0.0)
ErroredColor = (1.0, 0.0, 0.0)


# FUNCTIONS #

# initialize the socket
def socket_init():
    try:
        os.unlink(serverAddress)
    except OSError:
        if os.path.exists(serverAddress):
            raise

    server.bind(serverAddress)
    server.listen(1)
    print('Bound to socket ', serverAddress)

# close the socket


def socket_close():
    server.close()
    print('Unbound from socket ', serverAddress)

# response message to a request with a new value


def response_value(propertyName: str, propertyValue):
    return {
        'command': 'response',
        'property': propertyName,
        'value': propertyValue
    }

# response message with an error


def response_error(propertyName: str, command: str= '', errorMessage: str= 'generic error'):
    print('invalid {0} request to property \"{1}\": {2}'.format(
        command, propertyName, errorMessage), file=sys.stderr)

    return {'command': 'error'}


def handle_request(message, sock: socket):  # handle a request
    try:
        command = message['command']

        # GET Request
        if command == 'get':
            property_name = message['property']

            # validate Request
            if property_name not in property_getters:
                return response_error(property_name, command, 'unknown property')

            getter = property_getters[property_name]
            get_value = getter()

            # return the current value of property_name
            return response_value(property_name, get_value)

        # SET Request
        if command == 'set':
            property_name = str(message['property'])
            set_value = message['value']

            # validate request
            if property_name not in property_setters:
                return response_error(property_name, command, 'unknown property')
            if not set_value:
                return response_error(property_name, command, 'no value')

            # call the setter and get the new value
            setter = property_setters[property_name]
            get_value = setter(set_value)

            # return the current value of property_name
            return response_value(property_name, get_value)

        return response_error('UNKNOWN', command, 'unknown command')

    except KeyError:
        return response_error('UNKNOWN', '', 'invalid syntax')


def poll_loop():
    while True:
        # wait for a connection
        connection, client = server.accept()
        try:
            while True:
                # wait for data
                try:
                    data = connection.recv(2048)

                    if data:
                        # data received
                        message = json.loads(data.decode('utf-8'))

                        response = handle_request(message)
                        if response:
                            connection.send(json.dumps(response).encode('utf-8'))
                    else:
                        # no data received
                        # connection closed
                        break

                except socket.timeout:
                    print('Connection timed out', file=sys.stderr)
                    break
                except socket.error as e:
                    print('Connection I/O error:', file=sys.stderr)
                    print(e, file=sys.stderr)
                    break
                except json.JSONDecodeError as e:
                    print('Error decoding json:', file=sys.stderr)
                    print(e, file=sys.stderr)
                    break

        finally:
            connection.close()


# CALLBACKS #

# called when PSU turns on
def psu_status_on_cb():
    printer_state = PrinterState.IDLE


# called when PSU turns off
def psu_status_off_cb():
    printer_state = PrinterState.OFF


# called when the psu request switch is enabled
def psu_toggle_cb():
    psu_power_toggle()


# turns on the power supply and returns the power supply status
def psu_power_enable() -> bool:

    # check current power status
    if (psu_status.is_active is True):
        # psu is already on, cant enable
        print('Attempt to enable power supply that is already on!', file=sys.stderr)
        return True

    # enable the power on line and wait for the printer to turn on
    psu_power.on()
    psu_status.wait_for_press(psu_timeout)

    # check the new power state
    if psu_status.is_active is True:
        # set the printer to idle
        printer_state = PrinterState.IDLE
    else:
        # something has gone wrong, disable the power on line and log an error
        psu_power.off()
        print('Attempt to turn on power supply failed! Is the master power switch off?', file=sys.stderr)

    # return the new state
    return psu_status.is_active


def psu_power_disable() -> bool:
    # turns off the power supply, if not currently printing
    # returns the power supply status

    # check current power status
    if (psu_status.is_active is False):
        # psu is already off, cant disable
        print('Attempt to disable power supply that is already off!', file=sys.stderr)
        return False

    # refuse to turn off the printer if it is currently active
    if (printer_state is not PrinterState.OFF) and (printer_state is not PrinterState.IDLE):
        print('Blocking attempt to disable power supply while printing', file=sys.stderr)
        return True

    # disable the power on line and wait for the printer to turn off
    psu_power.off()
    psu_status.wait_for_release(psu_timeout)

    # check the new power state
    if psu_status.is_active is False:
        # set the printer to off
        printer_state = PrinterState.OFF
    else:
        # something has gone wrong, reenable the power on line and log an error
        psu_power.on()
        print('Attempt to turn off power supply failed!', file=sys.stderr)

    # return the new state
    return psu_status.is_active


# toggles the power supply and returns the power supply status
def psu_power_toggle() -> bool:
    psu_power_set(not psu_status.is_active)


# sets the power supply power to on or off and returns the power supply status
def psu_power_set(value: bool) -> bool:
    if value is True:
        return psu_power_enable()
    else:
        return psu_power_disable()


# gets the current power supply status
def psu_power_get() -> bool:
    return psu_status.is_active


# GPIO PINS #


# Grey wire
# Current status of the power supply, High when OK, low when off
psu_status = DigitalInputDevice(1, pull_up=False)

psu_status.when_activated = psu_status_on_cb
psu_status.when_deactivated = psu_status_off_cb

# White wire
# PSU request toggle, Low when switched
psu_toggle = Button(2, pull_up=True)

psu_toggle.when_pressed = psu_toggle_cb

# Purple wire
# PSU control output, low when on, high when off
psu_power = DigitalOutputDevice(3, active_high=False)

# Red, Green, and Blue wires
# RGB LED control sent to power transistors, low when off, high when on (NPN)
led = RGBLED(4, 5, 6)


class PrinterState(IntEnum):
    OFF = 0
    IDLE = 1
    HEATING = 2
    PRINTING = 3
    COMPLETE = 4
    CANCELED = 5
    ERRORED = 6


property_setters = {
    "psu_power": psu_power_set,
}

property_getters = {
    "psu_power": psu_power_get,
}

printer_state = PrinterState.OFF


def main():
    ticker = 0

    socket_init()

    while True:

        time.sleep(.1)
        pollSocket()


if __name__ == "__main__":
    main()
