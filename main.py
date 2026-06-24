import tkinter as tk
from tkinter import simpledialog, colorchooser
from xml.dom.minidom import ProcessingInstruction

import mido
import json
import time
import threading
from web_socket_handler import Dot2WebSocketHandler

DEBUG_MODE = True

# Midi controller
MIDI_INPORT = ""
MIDI_OUTPORT = ""
DEFAULT_INPUT_INDEX = 1
DEFAULT_OUTPUT_INDEX = 3

FADER_CC = (71, 72, 73, 74, 75, 76, 77, 78, 79)
NORMAL_BUTTON_NOTES = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63)
SPECIAL_BUTTON_NOTES = (100, 101, 102, 103, 104, 105, 106, 107, 112, 113, 114, 115, 116, 117, 118, 119)
SHIFT_KEY = (122)

note_executor_dictionnary = {}
BUTTON_COLORS = [107, 108, 96, 84, 60, 106, 120, 5, 89, 28, 29, 90, 77, 94, 57, 56, 105, 63, 111, 110, 73, 16, 20, 24, 97, 62, 100, 99, 109, 12, 113, 8, 64, 76, 21, 25, 75, 98, 74, 13, 104, 69, 41, 66, 68, 65, 102, 101, 93, 115, 70, 3, 117, 71, 112, 103, 114, 32, 36, 40, 91, 92, 44, 48]
DEFAULT_BRIGHTNESS_LEVEL = 6
COLOR_CYCLE_INTERVAL = 0.5

# Color cycling thread tracking
_color_cycle_threads = {}
_stop_color_cycle = {}

executor_states = {}
_executor_states_lock = threading.Lock()
execs_currently_on = []

# Dot2 Web Socket
HOST = "192.168.0.11"
USERNAME = "remote"
PLAINTEXT_PASSWORD = "1"
HEARTBEAT_STEP = 10

START_INDEX = [0, 100, 200, 300, 400, 500, 600, 700, 800]
ITEMS_COUNT = [22, 22, 22, 16, 16, 16, 16, 16, 16]

dot2_ws = Dot2WebSocketHandler(
    host=HOST,
    username=USERNAME,
    password=PLAINTEXT_PASSWORD,
    heartbeat_step=HEARTBEAT_STEP,
    debug=DEBUG_MODE,
    start_index=START_INDEX,
    items_count=ITEMS_COUNT
)

###################################################
#                 data management                 #
###################################################

def input(prompt=""):
    root = tk.Tk()
    root.withdraw()
    result = simpledialog.askstring("Input", prompt)
    root.destroy()
    return result

def load_json():
    global note_executor_dictionnary, cc_executor_dictionnary, BUTTON_COLORS, DEFAULT_BRIGHTNESS_LEVEL, COLOR_CYCLE_INTERVAL

    with open("data.json", "r") as data:
        data = json.load(data)

    note_executor_dictionnary = data["note_executor_dictionnary"]
    DEFAULT_BRIGHTNESS_LEVEL = data["default_brightness_level"]
    COLOR_CYCLE_INTERVAL = data.get("color_cycle_interval", 1)

    if DEBUG_MODE:
        print('================= JSON LOAD =================')
        print(f'Note executor dictionnary :', note_executor_dictionnary)
        print(f'Default brightness level :', DEFAULT_BRIGHTNESS_LEVEL)
        print(f'Color cycle interval :', COLOR_CYCLE_INTERVAL)
        print('================= JSON LOAD =================\n')

def append_note_to_json(note, colors, executor_index, pulse_channel, type="normal", filepath="data.json"):
    with open(filepath, "r") as f:
        data = json.load(f)

    data["note_executor_dictionnary"][str(note)] = {
        "executor_index": executor_index,
        "colors": colors,
        "pulse_channel": pulse_channel,
        "type": type
    }

    data["note_executor_dictionnary"] = dict(
        sorted(data["note_executor_dictionnary"].items(), key=lambda x: int(x[0]))
    )

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

#WIP
def handle_playbacks(data):
    execs_states = {}

    items_group = data.get("items_group")
    for exec_line in items_group:
        for exec in exec_line:
            exec_id = exec[0]["i"]["t"]
            exec_cues = exec[0]["cues"]["items"][0]["pgs"]

            if len(exec_cues) !=0:
                execs_states[str(exec_id)] = True

# WIP
def check_on_exec(interval=2):
    executor_states = {}
    stored_execs = {}

    #Initiate a dictionnary with execs turned off by default
    for note in note_executor_dictionnary.keys():
        stored_execs[note["executor_index"]] = False

    dot2_ws.poll_exec_state() #triggers handle playbacks






    def handle_pybacks(data):
        item_groups = data.get("itemGroups")  # note: "itemGroups" not "itemsGroups"
        if not item_groups:
            return

        new_states = {}
        blinking_buttons = set()

        for group in item_groups:
            items = group.get("items", [])
            for item_list in items:
                if not item_list:
                    continue
                item = item_list[0]
                exec_id = item.get("iExec")
                is_run = item.get("isRun", 0)
                if exec_id is not None:
                    new_states[exec_id] = bool(is_run)

        with _executor_states_lock:
            executor_states.clear()
            executor_states.update(new_states)

        # Check all stored buttons and update blinking state
        for note_str, button_data in note_executor_dictionnary.items():
            exec_index = button_data["executor_index"]
            button_type = button_data.get("type", "normal")

            if exec_index in new_states:
                is_on = new_states[exec_index]
                note_num = int(note_str)

                # Handle normal buttons
                if button_type == "normal":
                    colors = button_data["colors"]
                    if len(colors) > 1 and is_on:
                        _start_color_cycle(note_str)
                    elif not is_on:
                        _stop_color_cycle[note_str] = True
                        if colors:
                            msg = mido.Message('note_on', channel=DEFAULT_BRIGHTNESS_LEVEL,
                                               note=note_num, velocity=colors[0])
                            MIDI_OUTPORT.send(msg)
                    # else: is_on=True but single color → do nothing, keep current state


                # Handle special buttons
                elif button_type == "special":
                    if is_on:
                        # Blinking state for special buttons (channel 1, velocity 2)
                        msg = mido.Message('note_on', channel=1, note=note_num, velocity=2)
                        MIDI_OUTPORT.send(msg)
                    else:
                        # Turn off blinking
                        msg = mido.Message('note_on', channel=6, note=note_num, velocity=0)
                        MIDI_OUTPORT.send(msg)

    # Register persistent callback
    dot2_ws.on("itemsGroups", handle_playbacks)

    def poll_loop():
        REQUEST = {
            "requestType": "playbacks",
            "startIndex": [0, 100, 200, 300, 400, 500, 600, 700, 800],
            "itemsCount": [22, 22, 22, 16, 16, 16, 16, 16, 16],
            "pageIndex": 0,
            "itemsType": [3, 3, 3, 3, 3, 3, 3, 3, 3],
            "view": 3,
            "execButtonViewMode": 2,
            "buttonsViewMode": 0,
            "maxRequests": 1
        }
        while True:
            if dot2_ws.logged_in and dot2_ws.session_id is not None:
                REQUEST["session"] = dot2_ws.session_id
                dot2_ws._send(REQUEST)
            time.sleep(interval)

    thread = threading.Thread(target=poll_loop, daemon=True)
    thread.start()

    return executor_states

###################################################
#                       Midi                      #
###################################################

def select_midi_ports():
    global MIDI_INPORT, MIDI_OUTPORT

    available_inputs = mido.get_input_names()
    available_outputs = mido.get_output_names()
    temporary_input = ''
    temporary_output = ''

    if DEBUG_MODE:
        print('================= Input/Output Selection =================')

    if DEFAULT_INPUT_INDEX is None and DEFAULT_OUTPUT_INDEX is None:
        print("Please select an available input\n",'\n '.join(f"{i + 1}- {item}" for i, item in enumerate(available_inputs)))
        temporary_input = available_inputs[int(input("Please select an available input"))-1]

        print("\nPlease select an available output\n", '\n '.join(f"{i + 1}- {item}" for i, item in enumerate(available_outputs)))
        temporary_output = available_outputs[int(input("Please select an available output")) - 1]

    else:
        temporary_input = available_inputs[DEFAULT_INPUT_INDEX]
        temporary_output = available_outputs[DEFAULT_OUTPUT_INDEX]
    MIDI_INPORT = mido.open_input(temporary_input)
    MIDI_OUTPORT = mido.open_output(temporary_output)

    if DEBUG_MODE:
        print(f'Midi Inport :{MIDI_INPORT},\nMidi Outport :{MIDI_OUTPORT}')
        print('================= Input/Output Selection =================\n')

def listen_to_note():
    while True:
        message = MIDI_INPORT.receive()
        if message is not None:
            return message

def listen_to_note_on():
    while True:
        message = MIDI_INPORT.receive()
        if message is not None and message.type == 'note_on':
            return message

def link_executor_note(note):
    """
    Updates the data.json file
    :param note -> the MIDI note number to link
    """

    executor_index = int(input("Please input the id of the executor")) - 1
    if note in NORMAL_BUTTON_NOTES:
        num_colors = int(input("How many colors for this button?"))
        colors = choose_color(color_number=num_colors)
        pulse_channel = 10
        append_note_to_json(note, colors, executor_index, pulse_channel=pulse_channel, type="normal")

    elif note in SPECIAL_BUTTON_NOTES:
        colors = [1]
        append_note_to_json(note, colors, executor_index, pulse_channel=1, type="special")
    load_json()
    update_colors()

def note_loop():
    message = listen_to_note()

    note = message.note
    velocity = message.velocity
    note_is_stored = note_in_json(note)

    if DEBUG_MODE:
        print(f"Note received: {str(note)}, velocity: {velocity}")
        print(f"note in dict: {note_is_stored}")

    if int(note) in FADER_CC:
        return
    elif note_is_stored:
        executor_index = note_executor_dictionnary[str(note)]["executor_index"]
        dot2_ws.send_playback_click(executor_index, pressed=velocity == 127)
    elif not note_is_stored and message.type == 'note_on':
        link_executor_note(note)

def note_in_json(note):
    return str(note) in note_executor_dictionnary

def update_button_color(note):
    """Background thread that cycles through multiple colors for a button."""
    note_str = str(note)
    _stop_color_cycle[note_str] = False

    while not _stop_color_cycle.get(note_str, True):
        if note_str not in note_executor_dictionnary:
            break

        colors = note_executor_dictionnary[note_str]["colors"]
        if len(colors) <= 1:
            break

        for color_v in colors:
            if _stop_color_cycle.get(note_str, True):
                break

            velocity = color_v
            intensity = DEFAULT_BRIGHTNESS_LEVEL
            msg = mido.Message('note_on', channel=int(intensity), note=int(note_str), velocity=int(velocity))
            MIDI_OUTPORT.send(msg)
            time.sleep(COLOR_CYCLE_INTERVAL)

    _color_cycle_threads.pop(note_str, None)
    _stop_color_cycle.pop(note_str, None)

def choose_color(color_number):
    deactivate_color_cycles()
    color_tuple = []
    for i in range(color_number):
        for pad in range(len(BUTTON_COLORS)):
            msg = mido.Message('note_on', channel=6, note=pad, velocity=BUTTON_COLORS[pad])
            MIDI_OUTPORT.send(msg)

        message = listen_to_note_on()
        color_tuple.append(BUTTON_COLORS[message.note])

    activate_color_cycles()
    return color_tuple

def turn_off_pad(pad_list="All"):
    if pad_list == "All":

        # turn normal pads
        for pad in NORMAL_BUTTON_NOTES:
            msg = mido.Message('note_on', channel=6, note=pad, velocity=0)
            MIDI_OUTPORT.send(msg)

        # turn special pads
        for pad in SPECIAL_BUTTON_NOTES:
            msg = mido.Message('note_on', channel=1, note=pad, velocity=0)
            MIDI_OUTPORT.send(msg)
    else:
        # turn off given pads
        for pad in pad_list:
            msg = mido.Message('note_on', channel=6, note=pad, velocity=0)
            MIDI_OUTPORT.send(msg)

def update_colors():
    """Updates all colors of the pad including special buttons."""

    if DEBUG_MODE:
        print(f"\n================= Updating colors =================")
    # Deactivate all pads for a clean start
    print("Turning off all pads...")
    deactivate_color_cycles("All")
    turn_off_pad("All")
    print(print("Pads turned off.\n"))

    for button in note_executor_dictionnary:

        note_str = str(button)
        colors = note_executor_dictionnary[note_str]["colors"]
        button_type = note_executor_dictionnary[note_str]["type"]
        if DEBUG_MODE:
            print(f"\n================= Button [{button}] =================")
            print(f"Updating colors for button [{button}]...")
            print(f"note_str = {note_str}")
            print(f"colors = {colors}")
            print(f"button_type = {button_type}\n")

        #Handles different button types
        if button_type == "normal":
            intensity = DEFAULT_BRIGHTNESS_LEVEL
            first_velocity = colors[0]
            if DEBUG_MODE:
                print(f"first_velocity = {first_velocity}\nIntensity = {intensity}")

            # Send Midi Message(Update First Color)
            if DEBUG_MODE:
                print(f"Sending message to button, color updating...")
            msg = mido.Message('note_on', channel=int(intensity), note=int(note_str), velocity=int(first_velocity))
            MIDI_OUTPORT.send(msg)
            if DEBUG_MODE:
                print(f"Message sent to the button, color updated.")


            if DEBUG_MODE:
                print(f"Initiating color cycle...")
            if len(colors) > 1:
                _start_color_cycle(note_str)
            if DEBUG_MODE:
                print(f"Color cycle initiated.")



        elif button_type == "special":
            intensity = 1

            if DEBUG_MODE:
                print(f"Sending message to button, color updating...")
            msg = mido.Message('note_on', channel=0, note=int(note_str), velocity=1) # Channel 0 is the only channel that should be used with special buttons
            MIDI_OUTPORT.send(msg)
            if DEBUG_MODE:
                print(f"Message sent to the button, color updated.")

        elif button_type == "shift":
            pass
            #shift key doesn't have an LED
        print(f"================= Button [{button}] =================\n")

    if DEBUG_MODE:
        print(f"================= Colors Updated =================")

def deactivate_color_cycles(notes_to_deactivate="All"):
    if notes_to_deactivate == "All":
        for note_str in list(_stop_color_cycle.keys()):
            _stop_color_cycle[note_str] = True
    elif type(notes_to_deactivate) == list or type(notes_to_deactivate) == tuple:
        for note_str in list(notes_to_deactivate):
            _stop_color_cycle[note_str] = True

def activate_color_cycles(notes_to_activate="All"):
    if notes_to_activate == "All":
        for note_str in list(_stop_color_cycle.keys()):
            _stop_color_cycle[note_str] = False

def _start_color_cycle(note_str):
    """Helper to safely start a cycle thread, stopping any existing one first."""
    # Signal existing thread to stop
    _stop_color_cycle[note_str] = True

    # Wait briefly for old thread to exit
    old_thread = _color_cycle_threads.get(note_str)
    if old_thread and old_thread.is_alive():
        old_thread.join(timeout=COLOR_CYCLE_INTERVAL * 2 + 0.5)

    # Start fresh
    _stop_color_cycle[note_str] = False
    thread = threading.Thread(target=update_button_color, args=(note_str,), daemon=True)
    _color_cycle_threads[note_str] = thread
    thread.start()

###################################################
#                       Main                      #
###################################################

if DEBUG_MODE:
    print("==========================================\n========== DEBUG MODE ACTIVATED ==========\n==========================================\n")

load_json()
select_midi_ports()
dot2_ws.connect()
update_colors()

while not dot2_ws.logged_in:
    time.sleep(0.1)

while True:
    note_loop()