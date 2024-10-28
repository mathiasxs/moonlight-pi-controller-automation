#!/usr/bin/env python3

import sys
import signal
import logging
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GObject, GLib

import cec
import subprocess
import time

# config
GAMING_PC_IP = ""
GAMING_PC_MAC = "" # LAN-Adapter MAC
CONTROLLER_MAC = ""
MOONLIGHT_PARAMETERS = [] # https://github.com/moonlight-stream/moonlight-embedded/wiki/Usage
WAKE_UP_PC_TRIES = 10
WAKE_UP_PC_WAIT_SECONDS = 6
WAKE_UP_TV_WAIT_SECONDS = 3

# init
cec.init()
devices = cec.list_devices()

# business logic
BLUEZ_SERVICE_NAME = "org.bluez"
DBUS_OM_IFACE =      "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE =    "org.freedesktop.DBus.Properties"

LOG_FILE = "log_btminder.txt"
LOG_LEVEL = logging.ERROR
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

        # connected
        if properties["Connected"] == True:
            if properties["Address"] == CONTROLLER_MAC:
                start_streaming()

        # disconnected
        if properties["Connected"] == False:
            if properties["Address"] == CONTROLLER_MAC:
                stop_streaming()

    if "RSSI" in changed_props:
        dBs = properties["RSSI"]
        logger.info("Proximity {}: {} dB".format(properties["Address"], dBs))

def shutdown(signum, frame):
    mainloop.quit()

def start_streaming():
    start_tv() 
    start_moonlight()

    is_alive = wake_up_pc(WAKE_UP_PC_TRIES)
    if not is_alive:
        # failed to wake up pc
        logger.error("Error: PC couldn't be woken up")
        return

def stop_streaming():
    standby_tv()
    subprocess.Popen(['pkill', 'moonlight'])
    # TODO: send standby command to pc

# wake up pc
def wake_up_pc(tries):
    if (tries == 0):
        return False

    is_alive = subprocess.call(['ping', '-c', '1', GAMING_PC_IP], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) == 0
    if is_alive:
        return True

    logger.info(f"Sending wake command to gaming pc. Tries left: {tries-1}")
    subprocess.Popen('sudo /usr/sbin/etherwake -b ' + GAMING_PC_MAC.replace("-", ":"), shell=True, stdout=subprocess.PIPE)

    logger.info(f"Wait gaming pc {GAMING_PC_IP} {WAKE_UP_PC_WAIT_SECONDS} sec to wake up")
    time.sleep(WAKE_UP_PC_WAIT_SECONDS)

    return wake_up_pc(tries-1)

# start tv and connect
def start_tv():
    try: 
        devices = cec.list_devices()
        devices[0].power_on()
        cec.set_active_source(devices[0].address)

        logger.info(f"Wait TV {WAKE_UP_TV_WAIT_SECONDS} sec to wake up")
        time.sleep(WAKE_UP_TV_WAIT_SECONDS) # wait until TV is launched
    except: 
        logger.error("Unable to start TV")
        return

    logger.info("TV should be started")

# stop tv
def standby_tv():
    try: 
        devices = cec.list_devices()
        devices[0].standby()

        logger.info("TV is in standby")
    except: 
        logger.error("Unable to standby TV")

# start moonlight
def start_moonlight():
    subprocess.Popen(['moonlight-qt'] + MOONLIGHT_PARAMETERS + ['stream', GAMING_PC_IP, 'Desktop']) # start direct streaming (paired host required)
    # subprocess.Popen(['moonlight-qt'] + MOONLIGHT_PARAMETERS) # start only moonlight
    logger.info("Moonlight started")
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