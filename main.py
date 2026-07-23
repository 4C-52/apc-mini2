from web_socket_handler import Dot2WebSocketHandler
from tkinter import simpledialog
from datetime import datetime

import tkinter as tk
import mido
import os
import glob
import json
import time
import shutil
import keyboard
import threading

MIDI_INPORT_DEVICE1 = ""
MIDI_OUTPORT_DEVICE1 = ""
MIDI_INPORT_DEVICE2= ""
MIDI_OUTPORT_DEVICE2 = ""

DEFAULT_MIDI_INPORT_DEVICE1 = ""
DEFAULT_MIDI_OUTPORT_DEVICE1 = ""
DEFAULT_MIDI_INPORT_DEVICE2= ""
DEFAULT_MIDI_OUTPORT_DEVICE2 = ""
inverted_devices = False

FADER_NOTES = tuple(range(81,99))
NORMAL_BUTTON_NOTES = tuple(range(65))
SPECIAL_BUTTON_NOTES = (100, 101, 102, 103, 104, 105, 106, 107, 112, 113, 114, 115, 116, 117, 118, 119)
SHIFT_KEY = 122

note_executor_dictionary_device1 = {}
note_executor_dictionary_device2 = {}
executor_note_dictionary = {}
executor_states = set()
temporary_exec_states = set()

BUTTON_COLORS_DEVICE1 = list(range(0, 65))
BUTTON_COLORS_DEVICE2 = list(range(65,128))
DEFAULT_BRIGHTNESS_LEVEL = 6
DEFAULT_BLINK_CHANNEL = 10

# Dot2 Web Socket
HOST = "192.168.0.6"
USERNAME = "remote"
PLAINTEXT_PASSWORD = "1"
HEARTBEAT_STEP = 10
PERIODIC_PLAYBACK_INTERVAL = 3 # in seconds
BWING_START_INDEX=[300, 400, 500, 600, 700, 800]
BWING_ITEMS_COUNT=[16, 16, 16, 16, 16, 16]
BWING_ITEMS_TYPE=[3, 3, 3, 3, 3, 3]
BWING_VIEW=3
BWING_EXEC_VIEW_MODE=2

FWING_START_INDEX=[0, 100, 200]
FWING_ITEMS_COUNT=[22, 22, 22]
FWING_ITEMS_TYPE=[2, 3, 3]
FWING_VIEW=2
FWING_EXEC_VIEW_MODE=1

CONFIG_MODE = 1
DATA_FILEPATH = "data.json"


###################################################
#                   Tools/Utils                   #
###################################################

def input(prompt=""):
    root = tk.Tk()
    root.withdraw()
    result = simpledialog.askstring("Input", prompt)
    print(result)
    root.destroy()
    return result

def invert_devices():
    global MIDI_INPORT_DEVICE1, MIDI_INPORT_DEVICE2, MIDI_OUTPORT_DEVICE1, MIDI_OUTPORT_DEVICE2, inverted_devices

    MIDI_INPORT_DEVICE1, MIDI_INPORT_DEVICE2 = MIDI_INPORT_DEVICE2, MIDI_INPORT_DEVICE1
    MIDI_OUTPORT_DEVICE1, MIDI_OUTPORT_DEVICE2 = MIDI_OUTPORT_DEVICE2, MIDI_OUTPORT_DEVICE1

    inverted_devices = not inverted_devices
    set_correct_bmt_preset()

    update_colors()

def get_last_backup(backup_directory_path):
    backups = glob.glob(os.path.join(backup_directory_path, "data_backup_*.json"))
    if not backups:
        return None
    backups.sort()  # timestamp format YYYY-MM-DD_HH-MM sorts correctly as strings
    return backups[-1]

def restore_last_backup(filepath=DATA_FILEPATH):

    backup_directory_path = os.path.join(os.path.dirname(os.path.abspath(filepath)), "backups")
    last_backup = get_last_backup(backup_directory_path)

    if not last_backup:
        print("No backup found to restore.")
        return

    if input(f"Are you sure you want to load the last backup?(Y/N) \nYOUR CURRENT COLORS WILL BE OVERWRITTEN.").lower() == "y":
        if input(f"Type \"CONFIRM\" to load the last backup. Your current file will be LOST.") != "CONFIRM":
            return
    else:
        return

    shutil.copy2(last_backup, filepath)

    load_json()
    update_colors()

def initiate_executor_note_dictionary():
    global executor_note_dictionary, note_executor_dictionary_device1, note_executor_dictionary_device2

    executor_note_dictionary = {}
    # Organized as such : {"executor_id": [[note, device_id], [note, device_id]... ], executor_id:[[note, device_id]], ...}
    # This allows for multiple notes to be mapped to the same executor

    for note in note_executor_dictionary_device1.keys():
        executor = note_executor_dictionary_device1[note]["executor_index"]
        if executor not in executor_note_dictionary.keys():
            executor_note_dictionary[executor] = []
        executor_note_dictionary[executor].append([note, 1])

    for note in note_executor_dictionary_device2.keys():
        executor = note_executor_dictionary_device2[note]["executor_index"]
        if executor not in executor_note_dictionary.keys():
            executor_note_dictionary[executor] = []
        executor_note_dictionary[executor].append([note, 2])

def set_correct_bmt_preset():
    global inverted_devices

    if inverted_devices:
        send_midi_message("note_on", 0, 127, 67)
    else:
        send_midi_message("note_on", 0, 127, 69)

###################################################
#                      JSON                       #
###################################################

def load_json():
    global CONFIG_MODE, note_executor_dictionary_device1, note_executor_dictionary_device2, DEFAULT_BRIGHTNESS_LEVEL, PLAINTEXT_PASSWORD, HOST, DEFAULT_BLINK_CHANNEL, DEFAULT_MIDI_INPORT_DEVICE1, DEFAULT_MIDI_INPORT_DEVICE2, DEFAULT_MIDI_OUTPORT_DEVICE1, DEFAULT_MIDI_OUTPORT_DEVICE2

    with open(DATA_FILEPATH, "r") as data:
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

def append_note_to_json(note, executor_index, device_id, color=None, filepath=DATA_FILEPATH):
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

def set_default_devices(device1_input="", device1_output="", device2_input="", device2_output="", filepath=DATA_FILEPATH):
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

def toggle_config_mode(filepath=DATA_FILEPATH):
    global CONFIG_MODE

    CONFIG_MODE = not CONFIG_MODE

    with open(filepath, "r") as f:
        data = json.load(f)

    if CONFIG_MODE:
        flash_color(2, 5)
        data["config_mode"] = 1
    elif not CONFIG_MODE:
        flash_color(2, 21)
        data["config_mode"] = 0

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def remove_color_from_data(filepath=DATA_FILEPATH):
    flash_color(2, 120)
    with open(filepath, "r") as f:
        data = json.load(f)
    if input(f"Are you sure you want to remove all colors?(Y/N) \nA backup will be created.").lower() == "y":
        if input(f"Type \"CONFIRM\" to remove all colors from the stored data.") != "CONFIRM":
            return
    else:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")  # no colons!

    base_dir = os.path.dirname(os.path.abspath(filepath))
    backup_directory_path = os.path.join(base_dir, "backups")
    backup_filepath = os.path.join(backup_directory_path, f"data_backup_{timestamp}.json")

    os.makedirs(backup_directory_path, exist_ok=True)
    shutil.copy2(filepath, backup_filepath)

    with open(filepath, "r") as f:
        data = json.load(f)

    for note in data["note_executor_dictionary_device1"].keys():
        data["note_executor_dictionary_device1"][str(note)]["color"] = -1
    for note in data["note_executor_dictionary_device2"].keys():
        data["note_executor_dictionary_device2"][str(note)]["color"] = -1

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    load_json()
    update_colors()

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

    ###################################################
    #                      MIDI                       #
    ###################################################

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

def flash_color(duration, color):
    set_all_pads(velocity=color, channel=11)
    time.sleep(duration)
    update_colors()

def set_all_pads(velocity=0, channel=DEFAULT_BRIGHTNESS_LEVEL):
    for pad in NORMAL_BUTTON_NOTES:
        send_midi_message(midi_message_type="note_on", channel=channel, note=pad, velocity=velocity)

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
    set_all_pads(0, 6)

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
    update_all_blinking()

def set_colors(note_list, color, device_id):
    for note in note_list:
        send_midi_message("note_on", DEFAULT_BRIGHTNESS_LEVEL, note, velocity=color, device_id=device_id)

def toggle_blink_note(note, device_id, toggle_on):
    print(f"toggle-blink_note:\nNote: {note}\nDeviceId: {device_id}\ntoggle_on: {toggle_on}\n\n")
    if int(note) in SPECIAL_BUTTON_NOTES:
        if toggle_on:
            send_midi_message("note_on", 0, note, velocity=2, device_id=device_id)
        elif not toggle_on:
            send_midi_message("note_on", 0, note, velocity=1, device_id=device_id)
    elif int(note) in NORMAL_BUTTON_NOTES:
        if device_id == 1:
            color = note_executor_dictionary_device1[str(note)]["color"]
        elif device_id == 2:
            color = note_executor_dictionary_device2[str(note)]["color"]
        else:
            return

        if color == -1:
            return

        if toggle_on:
            send_midi_message("note_on", DEFAULT_BLINK_CHANNEL, note, velocity=color, device_id=device_id)
        elif not toggle_on:
            send_midi_message("note_on", DEFAULT_BRIGHTNESS_LEVEL, note, velocity=color, device_id=device_id)

def update_all_blinking():
    global executor_states, temporary_exec_states
    executor_states = set()
    temporary_exec_states = set()
    dot2_ws.poll_exec_state()

def dot2_logo():
    set_all_pads(109, 6)
    set_colors((8,9,11,12,13,14,15,16,17,19,23,28,37,38,47,51,55,60,61,62),3, 1)
    set_colors((8,11,13,14,15,16,19,22,24,25,26,27,30,32,35,38,40,43,45,46,47), 3, 2)

    ###################################################
    #                    Playbacks                    #
    ###################################################

def get_executor_state(data):
    """
    Takes the top-level data structure and returns a list of executor ids
    (from the 'i' field, the on-screen label) that are currently ON (isRun == 1).

    Each entry in data['items'] is itself a list (row) containing one or more
    executor dicts. We iterate through all of them and check 'isRun'.
    """
    running_ids = set()
    data_type = 0 # 0 If B-Wing, 1 if F-Wing
    if data.get("responseSubType", None) == 2:
        data_type = 1
    items_group = data.get("itemGroups", [])
    if len(items_group) == 0:
        return

    for row in items_group:
        for exec_item in row.get("items", []):
            exec_id = exec_item[0].get('iExec', None)
            if exec_item[0].get('isRun') == 1 and exec_id is not None:
                running_ids.add(exec_id)
    return running_ids, data_type

def handle_playbacks(data):
    global executor_states, temporary_exec_states
    """
    Takes the top-level data structure and serves as a hub for playback management, including feedback to the controller

    Because of how the websocket is made it is IMPOSSIBLE to get every executor in a single request.
    Therefore, handle_playbacks is called twice for every playback poll, that is because there are 2 request made by dot2_ws.poll_exec_state()
    This means that the data received is INCOMPLETE and you must keep that in mind, this data is not absolute.
    :param data:
    :return:
    """
    current_running_execs, exec_data_type = get_executor_state(data) # exec_data_type == 1 if data received is from F-Wing
    # F-Wing is always the second set of data to come in, therefore we know we treat the data if exec_data_type is equal to 1
    if exec_data_type == 0:
        temporary_exec_states = current_running_execs
    else:
        old_exec_states = executor_states
        current_running_execs = current_running_execs | temporary_exec_states # current_running_execs now contains every executor states
        print(f"Current running execs: {current_running_execs}")
        if old_exec_states == current_running_execs: # There's no need to continue if they're the same
            return
        old_current_symmetry = old_exec_states ^ current_running_execs # Only keep the ones that are different from each other, ^ is the symmetric difference operand

        for exec in old_current_symmetry:
            if exec in current_running_execs: # Executor was turned ON
                for temp in executor_note_dictionary[exec]:
                    # temp[0] = Note, temp[1] = device ID
                    print(f"Note ON: {temp[0]}")
                    toggle_blink_note(temp[0],temp[1], True)
            else: # Executor was turned OFF
                for temp in executor_note_dictionary[exec]:
                    # temp[0] = Note, temp[1] = device ID
                    print(f"Note OFF: {temp[0]}")
                    toggle_blink_note(temp[0],temp[1], False)
        executor_states = current_running_execs
        temporary_exec_states = set()

def periodic_playback_poll():
    while True:
        time.sleep(PERIODIC_PLAYBACK_INTERVAL)
        dot2_ws.poll_exec_state()

def note_loop(message, device_id):
    note = message.note
    if int(note) in FADER_NOTES:
        return

    if message.type == 'note_on' and CONFIG_MODE:
        link_executor_note(note, device_id)

    elif device_id == 1 and str(note) in note_executor_dictionary_device1:
        executor_index = note_executor_dictionary_device1[str(note)]["executor_index"]
        dot2_ws.send_playback_click(executor_index, pressed=message.velocity == 127)
        dot2_ws.poll_exec_state()

    elif device_id == 2 and str(note) in note_executor_dictionary_device2:
        executor_index = note_executor_dictionary_device2[str(note)]["executor_index"]
        dot2_ws.send_playback_click(executor_index, pressed=message.velocity == 127)
        dot2_ws.poll_exec_state()

# Load Data
load_json()
initiate_executor_note_dictionary()
select_midi_ports()
dot2_logo()

# Initiate the connexion
dot2_ws = Dot2WebSocketHandler(
    host=HOST,
    username=USERNAME,
    password=PLAINTEXT_PASSWORD,
    heartbeat_step=HEARTBEAT_STEP,

    bwing_start_index=BWING_START_INDEX,
    bwing_items_count=BWING_ITEMS_COUNT,
    bwing_items_type= BWING_ITEMS_TYPE,
    bwing_view=BWING_VIEW,
    bwing_exec_view_mode=BWING_EXEC_VIEW_MODE,

    fwing_start_index=FWING_START_INDEX,
    fwing_items_count=FWING_ITEMS_COUNT,
    fwing_items_type=FWING_ITEMS_TYPE,
    fwing_view=FWING_VIEW,
    fwing_exec_view_mode=FWING_EXEC_VIEW_MODE,

    debug=True,
)
dot2_ws.connect()


# waits for the websocket
while not dot2_ws.logged_in:
    time.sleep(0.1)

# Keybinds
keyboard.add_hotkey("F1", invert_devices)
keyboard.add_hotkey("F2", toggle_config_mode)
keyboard.add_hotkey("F11", restore_last_backup)
keyboard.add_hotkey("F12", remove_color_from_data)

time.sleep(2) # For the .2 logo to stay on

# Start Playback Polling
dot2_ws.on("playbacks", handle_playbacks)
update_colors()

periodic_playback_poll_thread = threading.Thread(target=periodic_playback_poll, daemon=True)
periodic_playback_poll_thread.start()

while True:
    #Listen for notes on both devices
    for msg in MIDI_INPORT_DEVICE1.iter_pending():
        note_loop(msg, device_id=1)

    for msg in MIDI_INPORT_DEVICE2.iter_pending():
        note_loop(msg, device_id=2)