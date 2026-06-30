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
DEFAULT_INPUT_INDEX = None
DEFAULT_OUTPUT_INDEX = None

FADER_CC = (71, 72, 73, 74, 75, 76, 77, 78, 79)
NORMAL_BUTTON_NOTES = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63)
SPECIAL_BUTTON_NOTES = (100, 101, 102, 103, 104, 105, 106, 107, 112, 113, 114, 115, 116, 117, 118, 119)
SHIFT_KEY = 122

note_executor_dictionary = {}
BUTTON_COLORS = [107, 108, 96, 84, 60, 106, 120, 5, 89, 28, 29, 90, 77, 94, 57, 56, 105, 63, 111, 110, 73, 16, 20, 24, 97, 62, 100, 99, 109, 12, 113, 8, 64, 76, 21, 25, 75, 98, 74, 13, 104, 69, 41, 66, 68, 65, 102, 101, 93, 115, 70, 3, 117, 71, 112, 103, 114, 32, 36, 40, 91, 92, 44, 48]
DEFAULT_BRIGHTNESS_LEVEL = 6
COLOR_CYCLE_INTERVAL = 0.2

# Color cycling thread tracking
_color_cycle_threads = {}
_stop_color_cycle = {}

executor_states = {}
_executor_states_lock = threading.Lock()
execs_currently_on = []
EXEC_STATE_CHECK_INTERVAL = 0.5
executor_states_thread = ""

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
    print(result)
    root.destroy()
    return result

def load_json():
    global note_executor_dictionary, BUTTON_COLORS, DEFAULT_BRIGHTNESS_LEVEL, COLOR_CYCLE_INTERVAL

    with open("data.json", "r") as data:
        data = json.load(data)

    note_executor_dictionary = data["note_executor_dictionary"]
    DEFAULT_BRIGHTNESS_LEVEL = data["default_brightness_level"]
    COLOR_CYCLE_INTERVAL = data.get("color_cycle_interval", 1)

    if DEBUG_MODE:
        print('================= JSON LOAD =================')
        print(f'Note executor dictionary :', note_executor_dictionary)
        print(f'Default brightness level :', DEFAULT_BRIGHTNESS_LEVEL)
        print(f'Color cycle interval :', COLOR_CYCLE_INTERVAL)
        print('================= JSON LOAD =================\n')

def append_note_to_json(note, colors, executor_index, pulse_channel, pad_type="normal", filepath="data.json"):
    with open(filepath, "r") as f:
        data = json.load(f)

    data["note_executor_dictionary"][str(note)] = {
        "executor_index": executor_index,
        "colors": colors,
        "pulse_channel": pulse_channel,
        "type": pad_type
    }

    data["note_executor_dictionary"] = dict(
        sorted(data["note_executor_dictionary"].items(), key=lambda x: int(x[0]))
    )

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def note_in_json(note):
    return str(note) in note_executor_dictionary

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

# WIP
def check_exec_state():
    global executor_states # stores the last states of the executor

    if DEBUG_MODE:
        print("Checking exec states...")

    while executor_states_thread.is_alive():
        time.sleep(EXEC_STATE_CHECK_INTERVAL)
        last_exec_state = executor_states
        current_exec_state = dot2_ws.poll_exec_state() #triggers handle playbacks

        print("last execs", last_exec_state)
        print("current execs", current_exec_state)

        '''execs_on = list(last_exec_state.keys() - current_exec_state.keys()) # Contains a list of executors that have been turned on since the last check
        execs_off = list(current_exec_state.keys() - last_exec_state.keys()) # idem with execs turned off

        if execs_on != []:
            for exec in execs_on:
                update_button_color(
                    executor_to_note(exec),
                    blink=True
                )

        if execs_off != []:
            for exec in execs_on:
                update_button_color(
                    executor_to_note(exec),
                    blink=False
                )

        executor_states = current_exec_state # Save the new executors states'''

def start_check_exec_state_loop():
    """Starts a thread that checks the state of execs in the background"""

    global executor_states_thread

    if DEBUG_MODE:
        print("Starting persistent check exec state callback...")
    # Register persistent callback
    dot2_ws.on("playbacks", handle_playbacks)

    executor_states_thread = threading.Thread(target=check_exec_state, daemon=True)
    executor_states_thread.start()

def executor_to_note(executor):
    """gives the note that's connected to the given executor"""
    # create a temporary dictionary with inverted executor index and note
    temp_dict = {
        value["executor_index"]: key
        for key, value in note_executor_dictionary.items()
    }

    return temp_dict[executor]

###################################################
#                       Midi                      #
###################################################

def select_midi_ports():
    global MIDI_INPORT, MIDI_OUTPORT

    available_inputs = mido.get_input_names()
    available_outputs = mido.get_output_names()

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

    temp = input("Please input the id of the executor")
    if temp is None:
        return
    executor_index = int(temp) - 1

    if note in NORMAL_BUTTON_NOTES:
        num_colors = int(input("How many colors for this button?"))
        colors = choose_color(color_number=num_colors)
        pulse_channel = 10
        append_note_to_json(note, colors, executor_index, pulse_channel=pulse_channel, pad_type="normal")

    elif note in SPECIAL_BUTTON_NOTES:
        colors = [1]
        append_note_to_json(note, colors, executor_index, pulse_channel=1, pad_type="special")
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
        executor_index = note_executor_dictionary[str(note)]["executor_index"]
        dot2_ws.send_playback_click(executor_index, pressed=velocity == 127)
    elif not note_is_stored and message.type == 'note_on':
        link_executor_note(note)

def send_midi_message(midi_message_type, channel, note, velocity):
    msg = mido.Message(type=str(midi_message_type), channel=int(channel), note=int(note), velocity=int(velocity))
    MIDI_OUTPORT.send(msg)

###################################################
#                      Colors                     #
###################################################

def update_button_color(note, blink = False):
    """Background thread that cycles through multiple colors for a button."""
    note_str = str(note)
    _stop_color_cycle[note_str] = False

    while not _stop_color_cycle.get(note_str, True):
        if note_str not in note_executor_dictionary:
            break

        colors = note_executor_dictionary[note_str]["colors"]
        if len(colors) <= 1:
            break

        for color_v in colors:
            if _stop_color_cycle.get(note_str, True):
                break

            velocity = color_v
            if not blink:
                intensity = DEFAULT_BRIGHTNESS_LEVEL
                send_midi_message(midi_message_type='note_on', channel=intensity, note=note_str, velocity=velocity)
            elif blink:
                intensity = note_executor_dictionary[note_str]["pulse_channel"]
                send_midi_message(midi_message_type='note_on', channel=intensity, note=note_str, velocity=velocity)
            time.sleep(COLOR_CYCLE_INTERVAL)

    _color_cycle_threads.pop(note_str, None)
    _stop_color_cycle.pop(note_str, None)

def choose_color(color_number):
    deactivate_color_cycles()
    color_tuple = []
    for i in range(color_number):
        for pad in range(len(BUTTON_COLORS)):
            send_midi_message(midi_message_type='note_on', channel=6, note=pad, velocity=BUTTON_COLORS[pad])

        message = listen_to_note_on()
        color_tuple.append(BUTTON_COLORS[message.note])

    activate_color_cycles()
    return color_tuple

def turn_off_pad(pad_list="All"):
    if pad_list == "All":

        # turn normal pads
        for pad in NORMAL_BUTTON_NOTES:
            send_midi_message(midi_message_type='note_on', channel=6, note=pad, velocity=0)

        # turn special pads
        for pad in SPECIAL_BUTTON_NOTES:
            send_midi_message(midi_message_type='note_on', channel=1, note=pad, velocity=0)
    else:
        # turn off given pads
        for pad in pad_list:
            send_midi_message(midi_message_type='note_on', channel=6, note=pad, velocity=0)

def update_colors():
    """Updates all colors of the pad including special buttons."""

    if DEBUG_MODE:
        print(f"\n================= Updating colors =================")
    # Deactivate all pads for a clean start
    print("Turning off all pads...")
    deactivate_color_cycles("All")
    turn_off_pad("All")
    print(print("Pads turned off.\n"))

    for button in note_executor_dictionary:

        note_str = str(button)
        colors = note_executor_dictionary[note_str]["colors"]
        button_type = note_executor_dictionary[note_str]["type"]
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
            send_midi_message(midi_message_type='note_on', channel=intensity, note=note_str, velocity=first_velocity)
            if DEBUG_MODE:
                print(f"Message sent to the button, color updated.")


            if DEBUG_MODE:
                print(f"Initiating color cycle...")
            if len(colors) > 1:
                _start_color_cycle(note_str)
            if DEBUG_MODE:
                print(f"Color cycle initiated.")



        elif button_type == "special":
            if DEBUG_MODE:
                print(f"Sending message to button, color updating...")
            send_midi_message(midi_message_type='note_on', channel=0, note=note_str, velocity=1) # Channel 0 is the only channel that should be used with special buttons

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

def toggle_blink(note, blink):
    """Toggle blinking on or off.
    Args:
        blink: Boolean, True if it should start blinking
        note: Integer, note to start/stop blinking
    """
    if note in NORMAL_BUTTON_NOTES:
        if blink:
            send_midi_message(
                midi_message_type='note_on',
                channel=note_executor_dictionary[note]["channel"],
                note=note,
                velocity=note_executor_dictionary[note]["velocity"],
            )




###################################################
#                       Main                      #
###################################################

if DEBUG_MODE:
    print("==========================================\n========== DEBUG MODE ACTIVATED ==========\n==========================================\n")

load_json()
select_midi_ports()
dot2_ws.connect()
update_colors()
# start_check_exec_state_loop()

while not dot2_ws.logged_in:
    time.sleep(0.1)

while True:
    note_loop()