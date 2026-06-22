import tkinter as tk
from tkinter import simpledialog, colorchooser
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
COLOR_CYCLE_INTERVAL = 1

# Color cycling thread tracking
_color_cycle_threads = {}
_stop_color_cycle = {}

# Dot2 Web Socket
HOST = "192.168.0.11"
USERNAME = "remote"
PLAINTEXT_PASSWORD = "1"
HEARTBEAT_STEP = 10

dot2_ws = Dot2WebSocketHandler(
    host=HOST,
    username=USERNAME,
    password=PLAINTEXT_PASSWORD,
    heartbeat_step=HEARTBEAT_STEP,
    debug=DEBUG_MODE
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

    if str(note) in FADER_CC:
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

        for color_hex in colors:
            if _stop_color_cycle.get(note_str, True):
                break

            velocity = color_hex
            intensity = DEFAULT_BRIGHTNESS_LEVEL
            msg = mido.Message('note_on', channel=int(intensity), note=int(note_str), velocity=int(velocity))
            MIDI_OUTPORT.send(msg)
            time.sleep(COLOR_CYCLE_INTERVAL)

    _color_cycle_threads.pop(note_str, None)
    _stop_color_cycle.pop(note_str, None)

def choose_color(color_number):
    if color_number > 1:
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
            msg = mido.Message('note_on', channel=6, note=pad, velocity=0)
            MIDI_OUTPORT.send(msg)
    else:
        # turn off given pads
        for pad in pad_list:
            msg = mido.Message('note_on', channel=6, note=pad, velocity=0)
            MIDI_OUTPORT.send(msg)

def update_colors():
    if DEBUG_MODE:
        print("================= Update Colors =================")
    # Stop all existing cycling threads
    if DEBUG_MODE:
        print("Stopping cycle threads")
    for note_str in list(_stop_color_cycle.keys()):
        _stop_color_cycle[note_str] = True

    if DEBUG_MODE:
        print("Turning off all pads")
    turn_off_pad()

    if DEBUG_MODE:
        print("Checking buttons stored")
    for button in note_executor_dictionnary:
        note_str = str(button)
        colors = note_executor_dictionnary[note_str]["colors"]

        if DEBUG_MODE:
            print(f"Pad: {note_str}; velocity: {colors}")

        intensity = DEFAULT_BRIGHTNESS_LEVEL

        # Set the first color immediately
        first_velocity = colors[0]
        msg = mido.Message('note_on', channel=int(intensity), note=int(note_str), velocity=int(first_velocity))
        MIDI_OUTPORT.send(msg)

        # Start a cycling thread if multiple colors
        if len(colors) > 1:
            _stop_color_cycle[note_str] = False
            thread = threading.Thread(target=update_button_color, args=(note_str,), daemon=True)
            _color_cycle_threads[note_str] = thread
            thread.start()

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
            _stop_color_cycle[note_str] = True

    elif type(notes_to_activate) == list or type(notes_to_activate) == tuple:
        for note_str in list(notes_to_activate):
            _stop_color_cycle[note_str] = True

###################################################
#                       Main                      #
###################################################

if DEBUG_MODE:
    print("==========================================\n========== DEBUG MODE ACTIVATED ==========\n==========================================\n")

load_json()
select_midi_ports()
dot2_ws.connect()
update_colors()

while True:
    note_loop()