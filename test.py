#!/usr/bin/env python3

import asyncio
import cec
import subprocess

# config
gaming_pc_ip = "192.168.178.64"
gaming_pc_mac = "D8-43-AE-54-66-8F" # LAN-Adapter MAC
moonlight_parameters = [] # https://github.com/moonlight-stream/moonlight-embedded/wiki/Usage

wake_up_pc_tries = 5
wake_up_pc_wait_seconds = 10

async def main():
    is_alive = await wake_up_pc(wake_up_pc_tries)
    if not is_alive:
        # failed to wake up pc
        print("Error: PC couldn't be woken up")
        return

    start_tv()
    start_moonlight()

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
    cec.init() # use default adapter
    devices = cec.list_devices()
    devices[0].power_on()
    cec.set_active_source(devices[0].address)
    print("TV should be started")

# start moonlight
def start_moonlight():
    subprocess.Popen(['moonlight-qt'] + moonlight_parameters + ['stream', gaming_pc_ip, 'Steam'])
    print("Moonlight started")
    # pkill moonlight if there are problems

asyncio.run(main())