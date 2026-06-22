import mido

MIDI_INPORT, MIDI_OUTPORT = "", ""
colors = {'#FFFFFF': 3, '#FF0000': 5, '#FFBD6C': 8, '#FFFF4C': 12, '#FFFF00': 13, '#88FF4C': 16, '#4CFF4C': 20, '#00FF00': 21, '#4CFF5E': 24, '#00FF19': 25, '#4CFF88': 28, '#00FF55': 29, '#4CFFB7': 32, '#4CC3FF': 36, '#4C88FF': 40, '#0055FF': 41, '#4C4CFF': 44, '#874CFF': 48, '#FF4C87': 56, '#FF0054': 57, '#FF1500': 60, '#795100': 62, '#436400': 63, '#033900': 64, '#005735': 65, '#00547F': 66, '#2500CC': 68, '#202020': 69, '#BDFF2D': 70, '#AFED06': 71, '#108B00': 73, '#00FF87': 74, '#002AFF': 75, '#3F00FF': 76, '#7A00FF': 77, '#59FF71': 84, '#D31DFF': 89, '#FF005D': 90, '#FF7F00': 91, '#B9B000': 92, '#90FF00': 93, '#835D07': 94, '#144C10': 96, '#0D5038': 97, '#15152A': 98, '#16205A': 99, '#693C1C': 100, '#A8000A': 101, '#DE513D': 102, '#D86A1C': 103, '#FFE126': 104, '#9EE12F': 105, '#67B50F': 106, '#1E1E30': 107, '#DCFF6B': 108, '#80FFBD': 109, '#9A99FF': 110, '#8E66FF': 111, '#404040': 112, '#757575': 113, '#E0FFFF': 114, '#A00000': 115, '#1AD000': 117, '#B35F00': 120}

# Work with a simple list of velocities indexed by pad number (0-63)
velocities = list(colors.values())  # index = pad position, value = color velocity

def select_midi_ports():
    global MIDI_INPORT, MIDI_OUTPORT
    available_inputs = mido.get_input_names()
    available_outputs = mido.get_output_names()

    print("Please select an available input")
    print('\n'.join(f"{i + 1}- {item}" for i, item in enumerate(available_inputs)))
    MIDI_INPORT = mido.open_input(available_inputs[int(input(">>> ")) - 1])

    print("\nPlease select an available output")
    print('\n'.join(f"{i + 1}- {item}" for i, item in enumerate(available_outputs)))
    MIDI_OUTPORT = mido.open_output(available_outputs[int(input(">>> ")) - 1])

def send_all_colors():
    for i in range(64):
        msg = mido.Message('note_on', channel=6, note=i, velocity=velocities[i])
        MIDI_OUTPORT.send(msg)

def listen_to_note():
    print('Listening...')
    while True:
        message = MIDI_INPORT.receive()
        if message.type == 'note_on' and message.velocity > 0:
            return message.note

select_midi_ports()
send_all_colors()

stop = False
while not stop:
    note1 = listen_to_note()
    note2 = listen_to_note()

    if note1 == 122 or note2 == 122:
        stop = True
    else:
        # Swap velocities at the two pressed pad positions
        velocities[note1], velocities[note2] = velocities[note2], velocities[note1]
        print(f"Swapped pads {note1} and {note2}")
        send_all_colors()
print(velocities)