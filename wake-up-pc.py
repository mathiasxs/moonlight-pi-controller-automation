
import asyncio
import subprocess

# config
gaming_pc_ip = "192.168.178.64"
gaming_pc_mac = "D8-43-AE-54-66-8F" # LAN-Adapter MAC
wake_up_pc_tries = 4
wake_up_pc_timeout_seconds = 3

# wake up pc
async def wake_up_pc(tries):
    if (tries == 0):
        return False
    
    is_alive = subprocess.call(['ping', '-c', '1', gaming_pc_ip], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) == 0
    if not is_alive:
        print(f"Sending wake command to gaming pc. Tries left: {tries-1}")
        subprocess.Popen('sudo /usr/sbin/etherwake -b ' + gaming_pc_mac.replace("-", ":"), shell=True, stdout=subprocess.PIPE)

        print(f"wait {wake_up_pc_timeout_seconds} sec")
        await asyncio.sleep(wake_up_pc_timeout_seconds)

        return await wake_up_pc(tries-1)
    else:
        return True
    
async def main():
    pc_woke_up = await wake_up_pc(wake_up_pc_tries)
    if not pc_woke_up:
        # failed to wake up pc
        print("Error: PC couldn't be woken up")
        return

asyncio.run(main())
