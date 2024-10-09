#!/usr/bin/env python3

import sys
import signal
import logging
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GObject, GLib

import asyncio
import cec
import subprocess
import time

# config
gaming_pc_ip = "192.168.178.64"
gaming_pc_mac = "D8-43-AE-54-66-8F" # LAN-Adapter MAC
moonlight_parameters = [] # https://github.com/moonlight-stream/moonlight-embedded/wiki/Usage
controller_mac = "28:C1:3C:5B:22:E0"

wake_up_pc_tries = 5
wake_up_pc_wait_seconds = 10

# init
cec.init()
devices = cec.list_devices()

# business logic
BLUEZ_SERVICE_NAME = "org.bluez"
DBUS_OM_IFACE =      "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE =    "org.freedesktop.DBus.Properties"

LOG_FILE = "log_btminder.txt"
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"

logging.basicConfig(filename=LOG_FILE, format=LOG_FORMAT, level=LOG_LEVEL)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
stream = logging.StreamHandler()
stream.setFormatter(logging.Formatter(LOG_FORMAT))
stream.setLevel(logging.DEBUG)

logger.addHandler(stream)

def device_property_changed_cb(iface, changed_props, invalidated_props, path=None, interface=None):
    if iface != "org.bluez.Device1":
        return
    device = dbus.Interface(bus.get_object("org.bluez", path), DBUS_PROP_IFACE)
    properties = device.GetAll("org.bluez.Device1")

# Replace with your code
    if "Connected" in changed_props:
        action = "connected" if properties["Connected"] else "disconnected"
        logger.info("The device {} [{}] is {}".format(properties["Alias"], properties["Address"], action))

        is_alive = wake_up_pc(wake_up_pc_tries)
        if not is_alive:
            # failed to wake up pc
            print("Error: PC couldn't be woken up")
            return

        start_tv()
        start_moonlight()

    if "RSSI" in changed_props:
        dBs = properties["RSSI"]
        logger.info("Proximity {}: {} dB".format(properties["Address"], dBs))

def shutdown(signum, frame):
    mainloop.quit()

# wake up pc
def wake_up_pc(tries):
    if (tries == 0):
        return False

    is_alive = subprocess.call(['ping', '-c', '1', gaming_pc_ip], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) == 0
    if is_alive:
        return True

    print(f"Sending wake command to gaming pc. Tries left: {tries-1}")
    subprocess.Popen('sudo /usr/sbin/etherwake -b ' + gaming_pc_mac.replace("-", ":"), shell=True, stdout=subprocess.PIPE)

    print(f"Wait {wake_up_pc_wait_seconds} sec")
    time.sleep(wake_up_pc_wait_seconds)

    return wake_up_pc(tries-1)

# start tv and connect
def start_tv():
    devices = cec.list_devices()
    devices[0].power_on()
    cec.set_active_source(devices[0].address)
    time.sleep(3)
    logger.info("TV should be started")

# start moonlight
def start_moonlight():
    subprocess.Popen(['moonlight-qt'] + moonlight_parameters + ['stream', gaming_pc_ip, 'Steam'])
    print("Moonlight started")
    # pkill moonlight if there are problems

if __name__ == "__main__":
    # shut down on a TERM signal
    signal.signal(signal.SIGTERM, shutdown)
    logger.info("Starting BTminder to monitor Bluetooth connections")

    # Get the system bus
    try:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
    except Exception as ex:
        logger.error("Unable to get the system bus: {}. Is D-Bus running? Exiting BTminder".format(ex.message))
        sys.exit(1)

    # listen for signals on the Bluez bus
    bus.add_signal_receiver(
            device_property_changed_cb,
            bus_name=BLUEZ_SERVICE_NAME,
            signal_name="PropertiesChanged",
            path_keyword="path",
            interface_keyword="interface")
    try:
        mainloop = GLib.MainLoop.new(None, False)
        mainloop.run()
    except KeyboardInterrupt:
        pass
    except:
        logger.error("Unable to run the GLib.MainLoop")

    logger.info("Shutting down BTminder")
    sys.exit(0)