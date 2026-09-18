# Controller-Triggered Game Streaming

Turn on the controller. The TV wakes up, the gaming PC wakes up, and the stream starts.
Turn the controller off and everything goes back to sleep.

No remote, no keyboard, no app to open. Picking up the controller is the only thing you do.

## How it works

A systemd service listens on D-Bus for Bluetooth connection events. Everything else follows
from one of them.

| Step | What happens | How |
|---|---|---|
| 1 | The controller connects over Bluetooth | BlueZ emits `PropertiesChanged` on D-Bus, the service matches the MAC |
| 2 | The TV turns on and switches input | HDMI-CEC `power_on` plus `set_active_source` |
| 3 | The gaming PC wakes up | Wake-on-LAN via `etherwake`, retried until `ping` answers |
| 4 | The stream starts | `moonlight-qt` connects to the host |
| 5 | The controller disconnects | TV to standby, `moonlight` terminated |

The interesting part is that these four systems know nothing about each other. Bluetooth,
HDMI, the network and the streaming client each have their own way of being told to wake
up, and none of them can be triggered by a game controller. The service is the piece that
turns one event into the whole chain.

## Requirements

**On the Pi**

- Python 3 with [PyGObject](https://pygobject.gnome.org/getting_started.html) for the
  D-Bus main loop
- [python-cec](https://github.com/trainman419/python-cec) for HDMI-CEC. Build it against
  `python3-dev`, not `python-dev`
- `etherwake`, callable through `sudo` without a password prompt
- `moonlight-qt`
- The Pi connected to the TV over HDMI, on a port that speaks CEC

**On the gaming PC**

- [Sunshine](https://github.com/LizardByte/Sunshine) as the streaming host, paired with
  the Pi once
- Wake-on-LAN enabled in the BIOS
- Automatic login, so the machine reaches the desktop without a keyboard
- **Fast startup turned off.** Windows otherwise performs a hybrid shutdown that powers the
  network adapter down, and Wake-on-LAN never reaches it. This is the single setting that
  breaks the whole chain most often

## Setup

Fill in the configuration block at the top of `controller-automation.py`:

```python
GAMING_PC_IP  = ""   # static, or a DHCP reservation
GAMING_PC_MAC = ""   # the LAN adapter, not Wi-Fi: Wake-on-LAN over Wi-Fi is unreliable
CONTROLLER_MAC = ""  # pair the controller once, then read its address from bluetoothctl
```

Then install the service:

```bash
sudo cp moonlight-pi-controller-automation.service /etc/systemd/system/
sudo systemctl enable --now moonlight-pi-controller-automation
```

The unit file points at an absolute script path. Adjust `ExecStart` to wherever the file
actually lives.

## Files

| File | Purpose |
|---|---|
| `controller-automation.py` | The service. Everything above happens here |
| `start-tv.py` | Turns the TV on over CEC. Useful for checking whether CEC works at all |
| `wake-up-pc.py` | Sends Wake-on-LAN and waits for a ping reply. Useful for checking the BIOS and fast-startup settings separately from everything else |

The two small scripts exist because debugging this chain from one end is painful. When
nothing happens, the question is always which of the four steps failed, and these answer it
one at a time.

## Known limitations

- **The TV is assumed to be the first CEC device.** `devices[0]` works on a setup with one
  display and no soundbar or receiver in between. With more devices on the bus it needs to
  match on the device address instead
- **No standby command to the PC.** Disconnecting the controller stops the stream and puts
  the TV to sleep, but the gaming PC stays on
- Logging goes to a file in the working directory, which under systemd is not where you
  would expect it
```
