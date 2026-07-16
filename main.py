import tkinter as tk
from tkinter import simpledialog

import mido
import json
import time
from web_socket_handler import Dot2WebSocketHandler

MIDI_INPORT_DEVICE1 = ""
MIDI_OUTPORT_DEVICE1 = ""
MIDI_INPORT_DEVICE2= ""
MIDI_OUTPORT_DEVICE2 = ""

DEFAULT_MIDI_INPORT_DEVICE1 = ""
DEFAULT_MIDI_OUTPORT_DEVICE1 = ""
DEFAULT_MIDI_INPORT_DEVICE2= ""
DEFAULT_MIDI_OUTPORT_DEVICE2 = ""

FADER_NOTES = (81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98)
NORMAL_BUTTON_NOTES = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63)
SPECIAL_BUTTON_NOTES = (100, 101, 102, 103, 104, 105, 106, 107, 112, 113, 114, 115, 116, 117, 118, 119)
SHIFT_KEY = 122

note_executor_dictionary_device1 = {}
note_executor_dictionary_device2 = {}
BUTTON_COLORS_DEVICE1 = [107, 108, 96, 84, 60, 106, 120, 5, 89, 28, 29, 90, 77, 94, 57, 56, 105, 63, 111, 110, 73, 16, 20, 24, 97, 62, 100, 99, 109, 12, 113, 8, 64, 76, 21, 25, 75, 98, 74, 13, 104, 69, 41, 66, 68, 65, 102, 101, 93, 115, 70, 3, 117, 71, 112, 103, 114, 32, 36, 40, 91, 92, 44, 48]
BUTTON_COLORS_DEVICE2 = BUTTON_COLORS_DEVICE1
DEFAULT_BRIGHTNESS_LEVEL = 6
DEFAULT_BLINK_CHANNEL = 10

# Dot2 Web Socket
HOST = "192.168.0.6"
USERNAME = "remote"
PLAINTEXT_PASSWORD = "1"
HEARTBEAT_STEP = 10

START_INDEX = [0, 100, 200, 300, 400, 500, 600, 700, 800]
ITEMS_COUNT = [22, 22, 22, 16, 16, 16, 16, 16, 16]

CONFIG_MODE = 1

def input(prompt=""):
    root = tk.Tk()
    root.withdraw()
    result = simpledialog.askstring("Input", prompt)
    print(result)
    root.destroy()
    return result

def load_json():
    global CONFIG_MODE, note_executor_dictionary_device1, note_executor_dictionary_device2, DEFAULT_BRIGHTNESS_LEVEL, PLAINTEXT_PASSWORD, HOST, DEFAULT_BLINK_CHANNEL, DEFAULT_MIDI_INPORT_DEVICE1, DEFAULT_MIDI_INPORT_DEVICE2, DEFAULT_MIDI_OUTPORT_DEVICE1, DEFAULT_MIDI_OUTPORT_DEVICE2

    with open("data.json", "r") as data:
        data = json.load(data)

    note_executor_dictionary_device1    =   data["note_executor_dictionary_device1"]
    note_executor_dictionary_device2    =   data["note_executor_dictionary_device2"]
    DEFAULT_BRIGHTNESS_LEVEL            =   data["default_brightness_level"]
    DEFAULT_BLINK_CHANNEL               =   data["default_blink_channel"]
    HOST                                =   data["default_ip_address"]
    PLAINTEXT_PASSWORD                  =   data["dot2_password"]
    CONFIG_MODE                         =   data["config_mode"]

    temp = data["DEFAULT_MIDI_INPORT_DEVICE1"]
    if temp != "":
        DEFAULT_MIDI_INPORT_DEVICE1     =   data["DEFAULT_MIDI_INPORT_DEVICE1"]

    temp = data["DEFAULT_MIDI_OUTPORT_DEVICE1"]
    if temp != "":
        DEFAULT_MIDI_OUTPORT_DEVICE1    =   data["DEFAULT_MIDI_OUTPORT_DEVICE1"]

    temp = data["DEFAULT_MIDI_INPORT_DEVICE2"]
    if temp != "":
        DEFAULT_MIDI_INPORT_DEVICE2     =   data["DEFAULT_MIDI_INPORT_DEVICE2"]

    temp = data["DEFAULT_MIDI_OUTPORT_DEVICE2"]
    if temp != "":
        DEFAULT_MIDI_OUTPORT_DEVICE2    =   data["DEFAULT_MIDI_OUTPORT_DEVICE2"]

def append_note_to_json(note, executor_index, device_id, color=None, filepath="data.json"):
    with open(filepath, "r") as f:
        data = json.load(f)

    if color is None:
        if device_id == 1:
            data["note_executor_dictionary_device1"][str(note)] = {
                "executor_index": executor_index,
            }
        elif device_id == 2:
            data["note_executor_dictionary_device2"][str(note)] = {
                "executor_index": executor_index,
            }
    else:
        if device_id == 1:
            data["note_executor_dictionary_device1"][str(note)] = {
                "executor_index": executor_index,
                "color": color
            }
        elif device_id == 2:
            data["note_executor_dictionary_device2"][str(note)] = {
                "executor_index": executor_index,
                "color": color
            }

    data["note_executor_dictionary_device1"] = dict(
        sorted(data["note_executor_dictionary_device1"].items(), key=lambda x: int(x[0]))
    )
    data["note_executor_dictionary_device2"] = dict(
        sorted(data["note_executor_dictionary_device2"].items(), key=lambda x: int(x[0]))
    )

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def set_default_devices(device1_input="", device1_output="", device2_input="", device2_output="", filepath="data.json"):
    """

    :param device1_input: # default = "" because if it was None it'd cause problems
    :param device1_output:
    :param device2_input:
    :param device2_output:
    :param filepath:
    :return:
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    if device1_input != "":
        data["DEFAULT_MIDI_INPORT_DEVICE1"]=device1_input
    if device2_input != "":
        data["DEFAULT_MIDI_INPORT_DEVICE2"]=device2_input
    if device1_output != "":
        data["DEFAULT_MIDI_OUTPORT_DEVICE1"]=device1_output
    if device2_output != "":
        data["DEFAULT_MIDI_OUTPORT_DEVICE2"]=device2_output

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

#WIP
def handle_playbacks(data):
    """
    Triggers when dot2_ws.poll_exec_state() is called and parses data to output a dictionary in this format :
    {"Exec_id": True, ...}
    True if the exec is on in Dot2
    Does not contain off execs
    :param data:
    :return:
    """
    execs_states = {}
    print("O"*50, data)
    items_group = data["itemGroups"]
    for exec_line in items_group:
        print(exec_line, "exec line")
        i_exec_off = exec_line["iExecOff"]
        for exec_struct in exec_line["items"]:
            print("exec", exec_struct)
            exec_id = exec_struct[0]["i"]["t"]
            if int(exec_id) < i_exec_off:
                exec_id = int(exec_id) + i_exec_off
            if exec_struct[0]['cues'] != {}:

                exec_cues = exec_struct[0]['cues']["items"][1]['pgs']['v']
            else:
                exec_cues = {}

            print("exec cues", exec_cues)
            print("exec_id", exec_id)

            if exec_cues>1:
                execs_states[str(exec_id)] = True
    print(execs_states)
    return execs_states

def select_midi_ports():
    global MIDI_INPORT_DEVICE1, MIDI_INPORT_DEVICE2, MIDI_OUTPORT_DEVICE1, MIDI_OUTPORT_DEVICE2, DEFAULT_MIDI_INPORT_DEVICE1, DEFAULT_MIDI_INPORT_DEVICE2, DEFAULT_MIDI_OUTPORT_DEVICE1, DEFAULT_MIDI_OUTPORT_DEVICE2

    available_inputs = mido.get_input_names()
    available_outputs = mido.get_output_names()

    if DEFAULT_MIDI_INPORT_DEVICE1 not in available_inputs:
        print("Please select the first device Input(Wing-1)\n",
              '\n '.join(f"{i + 1}- {item}" for i, item in enumerate(available_inputs)))
        temp = available_inputs[int(input("Please select an available input")) - 1]
        MIDI_INPORT_DEVICE1 = mido.open_input(temp)
        available_inputs.remove(temp)
        if input(f"Do you want to make {temp} your default INPUT device 1 ?(Y/N)").lower() == "y":
            DEFAULT_MIDI_INPORT_DEVICE1 = temp
    else:
        MIDI_INPORT_DEVICE1 = mido.open_input(DEFAULT_MIDI_INPORT_DEVICE1)

    if DEFAULT_MIDI_INPORT_DEVICE2 not in available_inputs:
        print("Please select the second device Input(Wing-2)\n",
              '\n '.join(f"{i + 1}- {item}" for i, item in enumerate(available_inputs)))
        temp = available_inputs[int(input("Please select an available input")) - 1]
        MIDI_INPORT_DEVICE2 = mido.open_input(temp)
        if input(f"Do you want to make {temp} your default INPUT device 2 ?(Y/N)").lower() == "y":
            DEFAULT_MIDI_INPORT_DEVICE2 = temp
    else:
        MIDI_INPORT_DEVICE2 = mido.open_input(DEFAULT_MIDI_INPORT_DEVICE2)

    if DEFAULT_MIDI_OUTPORT_DEVICE1 not in available_outputs:
        print("Please select the first device Output(Wing-1)\n",
              '\n '.join(f"{i + 1}- {item}" for i, item in enumerate(available_outputs)))
        temp = available_outputs[int(input("Please select an available output")) - 1]
        MIDI_OUTPORT_DEVICE1 = mido.open_output(temp)
        available_outputs.remove(temp)
        if input(f"Do you want to make {temp} your default OUTPUT device 1 ?(Y/N)").lower() == "y":
            DEFAULT_MIDI_OUTPORT_DEVICE1 = temp
    else:
        MIDI_OUTPORT_DEVICE1 = mido.open_output(DEFAULT_MIDI_OUTPORT_DEVICE1)

    if DEFAULT_MIDI_OUTPORT_DEVICE2 not in available_outputs:
        print("Please select the second device Output(Wing-2)\n",
              '\n '.join(f"{i + 1}- {item}" for i, item in enumerate(available_outputs)))
        temp = available_outputs[int(input("Please select an available output")) - 1]
        MIDI_OUTPORT_DEVICE2 = mido.open_output(temp)
        if input(f"Do you want to make {temp} your default OUTPUT device 2 ?(Y/N)").lower() == "y":
            DEFAULT_MIDI_OUTPORT_DEVICE2 = temp
    else:
        MIDI_OUTPORT_DEVICE2 = mido.open_output(DEFAULT_MIDI_OUTPORT_DEVICE2)


    set_default_devices(device1_input=DEFAULT_MIDI_INPORT_DEVICE1,device2_input=DEFAULT_MIDI_INPORT_DEVICE2,device1_output=DEFAULT_MIDI_OUTPORT_DEVICE1,device2_output=DEFAULT_MIDI_OUTPORT_DEVICE2)
    print(f"Midi Device IN 1: {MIDI_INPORT_DEVICE1}\nMidi Device IN 2: {MIDI_INPORT_DEVICE2}\nMIDI Device OUT 1: {MIDI_OUTPORT_DEVICE1}\nMIDI Device OUT 2: {MIDI_OUTPORT_DEVICE2}\n")

def link_executor_note(note, device_id):
    """
    Updates the data.json file
    :param note -> the MIDI note number to link
    :param device_id -> the device ID to link the executor to, check GitHub to know device IDs
    """
    if device_id == 1 and str(note) in note_executor_dictionary_device1.keys():
        executor_index = note_executor_dictionary_device1[str(note)]["executor_index"]
    elif device_id == 2 and str(note) in note_executor_dictionary_device2.keys():
        executor_index = note_executor_dictionary_device2[str(note)]["executor_index"]
    else:
        temp = input("Please input the id of the executor")
        if temp is None:
            return
        executor_index = int(temp) - 1

    if note in NORMAL_BUTTON_NOTES:
        color = choose_color()
        append_note_to_json(note, executor_index, device_id=device_id, color=color)

    elif note in SPECIAL_BUTTON_NOTES or note == SHIFT_KEY:
        append_note_to_json(note, executor_index, device_id=device_id, color=1)

    load_json()
    update_colors()

def note_loop(message, device_id):
    note = message.note
    if int(note) in FADER_NOTES:
        return

    if message.type == 'note_on' and CONFIG_MODE:
        link_executor_note(note, device_id)

    elif device_id == 1 and str(note) in note_executor_dictionary_device1:
        executor_index = note_executor_dictionary_device1[str(note)]["executor_index"]
        dot2_ws.send_playback_click(executor_index, pressed=message.velocity == 127)

    elif device_id == 2 and str(note) in note_executor_dictionary_device2:
        executor_index = note_executor_dictionary_device2[str(note)]["executor_index"]
        dot2_ws.send_playback_click(executor_index, pressed=message.velocity == 127)

def send_midi_message(midi_message_type, channel, note, velocity, device_id=3):
    midi_message = mido.Message(type=str(midi_message_type), channel=int(channel), note=int(note), velocity=int(velocity))
    if device_id == 1:
        MIDI_OUTPORT_DEVICE1.send(midi_message)
    elif device_id == 2:
        MIDI_OUTPORT_DEVICE2.send(midi_message)
    else:
        MIDI_OUTPORT_DEVICE1.send(midi_message)
        MIDI_OUTPORT_DEVICE2.send(midi_message)

def listen_to_note():
    while True:
        for incoming_message in MIDI_INPORT_DEVICE1.iter_pending():
            return incoming_message, 1

        for incoming_message in MIDI_INPORT_DEVICE2.iter_pending():
            return incoming_message, 2

def choose_color():
    color_velocity = 0
    for pad in range(len(BUTTON_COLORS_DEVICE1)):
        send_midi_message(midi_message_type='note_on', channel=6, note=pad, velocity=BUTTON_COLORS_DEVICE1[pad],device_id=1)

    for pad in range(len(BUTTON_COLORS_DEVICE2)):
        send_midi_message(midi_message_type='note_on', channel=6, note=pad, velocity=BUTTON_COLORS_DEVICE2[pad],device_id=2)

    message, device_id = listen_to_note()
    while message.type != 'note_on':
        message,device_id = listen_to_note()
        if message.note not in NORMAL_BUTTON_NOTES:
            return -1
    if device_id == 1:
        color_velocity = BUTTON_COLORS_DEVICE1[message.note]
    elif device_id == 2:
        color_velocity = BUTTON_COLORS_DEVICE2[message.note]
    return color_velocity

def turn_off_pad():
    for pad in NORMAL_BUTTON_NOTES:
        send_midi_message(midi_message_type='note_on', channel=6, note=pad, velocity=0)

    for pad in SPECIAL_BUTTON_NOTES:
        send_midi_message(midi_message_type='note_on', channel=0, note=pad, velocity=0)

def update_colors():
    """Updates all colors of the pad including special buttons."""
    turn_off_pad()
    note_executor_dictionaries = [note_executor_dictionary_device1, note_executor_dictionary_device2]

    for device in range(2):
        for button_note in note_executor_dictionaries[device]:
            color = note_executor_dictionaries[device][button_note]["color"]
            if color < 0:
                continue

            #Handles different button types
            if int(button_note) in NORMAL_BUTTON_NOTES:
                intensity = DEFAULT_BRIGHTNESS_LEVEL
                send_midi_message(midi_message_type='note_on', channel=intensity, note=button_note, velocity=color, device_id=device+1)

            elif int(button_note) in SPECIAL_BUTTON_NOTES:
                send_midi_message(midi_message_type='note_on', channel=0, note=button_note, velocity=1, device_id=device+1) # Channel 0 is the only channel that should be used with special buttons

load_json()

dot2_ws = Dot2WebSocketHandler(
    host=HOST,
    username=USERNAME,
    password=PLAINTEXT_PASSWORD,
    heartbeat_step=HEARTBEAT_STEP,
    start_index=START_INDEX,
    items_count=ITEMS_COUNT
)

select_midi_ports()
dot2_ws.connect()
update_colors()

while not dot2_ws.logged_in:
    time.sleep(0.1)

while True:
    for msg in MIDI_INPORT_DEVICE1.iter_pending():
        note_loop(msg, device_id=1)

    for msg in MIDI_INPORT_DEVICE2.iter_pending():
        note_loop(msg, device_id=2)