import cec

cec.init() # use default adapter
devices = cec.list_devices()
devices[0].power_on()
cec.set_active_source(devices[0].address)
print("TV should be started")