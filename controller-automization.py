#!/usr/bin/env python3

from dbus_next.aio import MessageBus

import asyncio
import cec
import subprocess
import time

# config
gaming_pc_ip = "192.168.178.64"
gaming_pc_mac = "D8-43-AE-54-66-8F" # LAN-Adapter MAC
moonlight_parameters = ['-4k', '-fps 60', '-bitrate 40', '-quitappafter'] # https://github.com/moonlight-stream/moonlight-embedded/wiki/Usage

wake_up_pc_tries = 3
wake_up_pc_wait_seconds = 10

# init
cec.init()
devices = cec.list_devices()
loop = asyncio.get_event_loop()

async def receive_connected_event():
    bus = await MessageBus().connect()
    introspection = await bus.introspect('org.bluez', "/")
    obj = bus.get_proxy_object('org.bluez', "/", introspection) 
    device = obj.get_interface('org.bluez.Device1') # ?
    properties = obj.get_interface('org.freedesktop.DBus.Properties')

    async def device_property_changed_cb(interface_name, changed_properties, invalidated_properties):
        for changedPropertyName, variant in changed_properties.items():
            print(f'property changed: {changedPropertyName} - {variant.value}')

            if (changedPropertyName == "Connected" and variant.value == True):
                is_alive = await wake_up_pc(wake_up_pc_tries)
                if not is_alive:
                    # failed to wake up pc
                    print("Error: PC couldn't be woken up")
                    return

                start_tv()
                start_moonlight()
            # else:
                # close moonlight-qt
                # power off TV
                # shutdown pc

    properties.on_properties_changed(device_property_changed_cb)

    await loop.create_future()

# wake up pc
async def wake_up_pc(tries):
    if (tries == 0):
        return False

    is_alive = subprocess.call(['ping', '-c', '1', gaming_pc_ip], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) == 0
    if is_alive:
        return True

    print(f"Sending wake command to gaming pc. Tries left: {tries-1}")
    subprocess.Popen('sudo /usr/sbin/etherwake -b ' + gaming_pc_mac.replace("-", ":"), shell=True, stdout=subprocess.PIPE)

    print(f"Wait {wake_up_pc_wait_seconds} sec")
    await asyncio.sleep(wake_up_pc_wait_seconds)

    return await wake_up_pc(tries-1)

# start tv and connect
def start_tv():
    devices = cec.list_devices()
    devices[0].power_on()
    cec.set_active_source(devices[0].address)
    print("TV should be started")

# start moonlight
def start_moonlight():
    subprocess.Popen(['moonlight-qt', 'stream'] + moonlight_parameters + [gaming_pc_ip])
    print("Moonlight started")

loop.run_until_complete(receive_connected_event())