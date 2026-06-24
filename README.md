# APC Mini MK2 → Dot2 MIDI Bridge

## Purpose

This software allows you to easily link an **Akai APC Mini MK2** MIDI controller to a **GrandMA Dot2** lighting console via its WebSocket API. Each pad on the controller can be mapped to an executor on the Dot2, with customizable colors and multi-color cycling support.

> ⚠️ **Note:** Special buttons and faders are not yet fully supported but will be implemented in a future update.

---

## Installation

### Requirements

- Python 3.8+
- The following Python packages:

```bash
pip install mido python-rtmidi websocket-client
```

    ⚠️ Make sure to install python-rtmidi and not rtmidi — they are different packages and only python-rtmidi will work correctly with mido.

Configuration

Before running the software, open main.py and update the following variables at the top of the file:

HOST = "192.168.0.11"       # Replace with your Dot2 console's IP address
PLAINTEXT_PASSWORD = "1"    # Replace with the remote password set in Dot2

    HOST: The IP address of your Dot2 console. You can find it in the console under Setup > Global Settings.
    PLAINTEXT_PASSWORD: The password configured for remote access in Dot2.

How to Use

    Launch your Dot2 console and make sure it is connected to the same network as your computer.

    Run the script:

python main.py

    Select your MIDI ports when prompted — choose the same ports that are configured in Dot2 under Tools > MIDI Configuration.

    Press any unassigned pad on the APC Mini MK2. The software will prompt you to:
        Enter the executor number — you can find this by pressing the MA key on the Dot2 and hovering over the desired executor.
        Enter the number of colors you want to assign to that pad.
        Press the desired color(s) on the lit-up controller to confirm your selection.

    The pad is now linked to the executor. Press it to trigger the executor on the Dot2. If multiple colors were assigned, the pad will cycle through them while the executor is active.

