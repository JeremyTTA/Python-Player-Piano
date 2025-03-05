import tkinter as tk
from tkinter import ttk
import mido
import time
import json  # Import json module

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

class SynthesiaKeyboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Standlee Player Piano")
        self.geometry("800x400")  # Initial window size
        self.bind("<Configure>", self.on_resize)

        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True, anchor=tk.SW)

        self.active_keys = {}
        self.key_colors = {}  # New dictionary to store original colors

        self.load_window_size()  # Load saved window size

        self.draw_keyboard()
        self.midi_output = None
        self.midi_input = None
        self.create_midi_controls()
        self.create_status_labels()

        self.load_midi_ports()  # Load saved MIDI ports

        self.indicator_rect = None  # Initialize the indicator rectangle
        self.indicator_counter = 0  # Initialize the counter
        self.indicator_text = None  # Initialize the indicator text
        self.indicator_color = "green"  # Initialize the indicator color
        self.create_indicator_rect()  # Create the indicator rectangle

        self.start_time = None  # Initialize start time for round trip calculation

    def create_indicator_rect(self):
        self.indicator_counter += 1  # Increment the counter
        width = self.winfo_width()
        height = self.winfo_height()
        rect_size = 40  # Size of the rectangle
        x0 = (width - rect_size) // 2
        y0 = (height - rect_size) // 2
        x1 = x0 + rect_size
        y1 = y0 + rect_size
        if self.indicator_rect:
            self.canvas.coords(self.indicator_rect, x0, y0, x1, y1)
            self.canvas.itemconfig(self.indicator_rect, fill=self.indicator_color)  # Maintain the current color
        else:
            self.indicator_rect = self.canvas.create_rectangle(x0, y0, x1, y1, fill=self.indicator_color, outline="white")
        if self.indicator_text:
            self.canvas.coords(self.indicator_text, (x0 + x1) // 2, (y0 + y1) // 2)
        else:
            self.indicator_text = self.canvas.create_text((x0 + x1) // 2, (y0 + y1) // 2, text=str(self.indicator_counter), fill="white")

    def on_resize(self, event):
        self.save_window_size()  # Save window size on resize
        self.canvas.delete("all")
        self.draw_keyboard()
        self.create_indicator_rect()  # Recreate the indicator rectangle after drawing the keyboard

    def save_window_size(self):
        size = {
            "width": self.winfo_width(),
            "height": self.winfo_height()
        }
        with open("window_size.json", "w") as f:
            json.dump(size, f)

    def load_window_size(self):
        try:
            with open("window_size.json", "r") as f:
                size = json.load(f)
                self.geometry(f'{size["width"]}x{size["height"]}')
        except FileNotFoundError:
            pass

    def draw_keyboard(self):
        width = self.winfo_width()
        height = self.winfo_height() // 4  # 1/4 of the window height (increased height)
        white_key_width = width / 52  # 52 white keys
        black_key_width = white_key_width * 2 / 3  # Black keys are narrower
        black_key_height = height * 3 / 5  # Black keys are shorter

        # Draw blue line above the keyboard
        self.canvas.create_line(0, self.winfo_height() - height - 2, width, self.winfo_height() - height - 2, fill="blue", width=4)

        # Draw white keys
        white_key_notes = [21, 23, 24, 26, 28, 29, 31, 33, 35, 36, 38, 40, 41, 43, 45, 47, 48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84, 86, 88, 89, 91, 93, 95, 96, 98, 100, 101, 103, 105, 107, 108]  # MIDI note numbers for white keys starting from A0
        for i, note in enumerate(white_key_notes):
            x0 = i * white_key_width
            x1 = x0 + white_key_width
            y0 = self.winfo_height() - height
            y1 = self.winfo_height()
            key_id = self.canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="black")
            self.canvas.tag_bind(key_id, "<ButtonPress-1>", lambda e, k=key_id: self.on_key_click(e, k))
            self.canvas.tag_bind(key_id, "<ButtonRelease-1>", lambda e, k=key_id: self.on_key_release(e, k))
            self.active_keys[key_id] = note  # Assign MIDI note number
            self.key_colors[key_id] = "white"  # Store original color

        # Draw black keys
        black_key_notes = [22, 25, 27, 30, 32, 34, 37, 39, 42, 44, 46, 49, 51, 54, 56, 58, 61, 63, 66, 68, 70, 73, 75, 78, 80, 82, 85, 87, 90, 92, 94, 97, 99, 102, 104, 106]  # MIDI note numbers for black keys
        black_key_positions = [1, 3, 4, 6, 7, 8]  # Positions of black keys in an octave
        for i, note in enumerate(black_key_notes):
            octave = i // 5
            pos = i % 5
            x0 = (octave * 7 + black_key_positions[pos]) * white_key_width - black_key_width / 2
            x1 = x0 + black_key_width
            y0 = self.winfo_height() - height
            y1 = y0 + black_key_height
            key_id = self.canvas.create_rectangle(x0, y0, x1, y1, fill="black", outline="white")
            self.canvas.tag_bind(key_id, "<ButtonPress-1>", lambda e, k=key_id: self.on_key_click(e, k))
            self.canvas.tag_bind(key_id, "<ButtonRelease-1>", lambda e, k=key_id: self.on_key_release(e, k))
            self.active_keys[key_id] = note  # Assign MIDI note number
            self.key_colors[key_id] = "black"  # Store original color

        # Draw the last black key in the 8th octave
        x0 = 7 * 7 * white_key_width + black_key_positions[0] * white_key_width - black_key_width / 2
        x1 = x0 + black_key_width
        y0 = self.winfo_height() - height
        y1 = y0 + black_key_height
        key_id = self.canvas.create_rectangle(x0, y0, x1, y1, fill="black", outline="white")
        self.canvas.tag_bind(key_id, "<ButtonPress-1>", lambda e, k=key_id: self.on_key_click(e, k))
        self.canvas.tag_bind(key_id, "<ButtonRelease-1>", lambda e, k=key_id: self.on_key_release(e, k))
        self.active_keys[key_id] = 108  # Assign MIDI note number for the last black key
        self.key_colors[key_id] = "black"  # Store original color

    def create_midi_controls(self):
        control_frame = tk.Frame(self, bg="black")
        control_frame.place(relx=0.0, rely=0.0, x=10, y=10, anchor='nw')

        # MIDI Input Label
        input_label = tk.Label(control_frame, text="MIDI Input:", fg="white", bg="black")
        input_label.grid(row=0, column=0, padx=5, pady=5)

        # MIDI Input Dropdown
        self.midi_input_var = tk.StringVar()
        self.midi_input_dropdown = ttk.Combobox(control_frame, textvariable=self.midi_input_var)
        self.midi_input_dropdown['values'] = ["None"] + mido.get_input_names()
        self.midi_input_dropdown.grid(row=0, column=1, padx=5, pady=5)

        # MIDI Input Status Circle
        self.midi_input_status = tk.Canvas(control_frame, width=20, height=20, bg="black", highlightthickness=0)
        self.midi_input_status.create_oval(0, 0, 20, 20, fill="red")
        self.midi_input_status.grid(row=0, column=2, padx=5, pady=5)

        # MIDI Output Label
        output_label = tk.Label(control_frame, text="MIDI Output:", fg="white", bg="black")
        output_label.grid(row=1, column=0, padx=5, pady=5)

        # MIDI Output Dropdown
        self.midi_output_var = tk.StringVar()
        self.midi_output_dropdown = ttk.Combobox(control_frame, textvariable=self.midi_output_var)
        self.midi_output_dropdown['values'] = ["None"] + mido.get_output_names()
        self.midi_output_dropdown.grid(row=1, column=1, padx=5, pady=5)

        # MIDI Output Status Circle
        self.midi_output_status = tk.Canvas(control_frame, width=20, height=20, bg="black", highlightthickness=0)
        self.midi_output_status.create_oval(0, 0, 20, 20, fill="red")
        self.midi_output_status.grid(row=1, column=2, padx=5, pady=5)

        self.midi_input_var.trace("w", self.update_midi_ports)
        self.midi_output_var.trace("w", self.update_midi_ports)
        self.check_midi_status()

    def save_midi_ports(self):
        ports = {
            "input": self.midi_input_var.get(),
            "output": self.midi_output_var.get()
        }
        with open("midi_ports.json", "w") as f:
            json.dump(ports, f)

    def load_midi_ports(self):
        try:
            with open("midi_ports.json", "r") as f:
                ports = json.load(f)
                self.midi_input_var.set(ports.get("input", ""))
                self.midi_output_var.set(ports.get("output", ""))
        except FileNotFoundError:
            pass

    def create_status_labels(self):
        status_frame = tk.Frame(self, bg="black")
        status_frame.place(relx=0.0, rely=0.0, x=10, y=70, anchor='nw')

        self.key_status_label = tk.Label(status_frame, text="Key Pressed: None", fg="white", bg="black", width=30, anchor='w', wraplength=300)
        self.key_status_label.grid(row=0, column=0, padx=5, pady=5)

        self.midi_status_label = tk.Label(status_frame, text="MIDI Input: None", fg="white", bg="black", width=30, anchor='w', wraplength=300)
        self.midi_status_label.grid(row=1, column=0, padx=5, pady=5)

        self.round_trip_label = tk.Label(status_frame, text="Round Trip Time: N/A", fg="white", bg="black", width=30, anchor='w', wraplength=300)
        self.round_trip_label.grid(row=2, column=0, padx=5, pady=5)

    def check_midi_status(self):
        input_connected = self.midi_input_var.get() in mido.get_input_names()
        output_connected = self.midi_output_var.get() in mido.get_output_names()

        self.midi_input_status.itemconfig(1, fill="green" if input_connected else "red")
        self.midi_output_status.itemconfig(1, fill="green" if output_connected else "red")

        self.after(1000, self.check_midi_status)  # Check status every second

    def update_midi_ports(self, *args):
        if self.midi_input:
            self.midi_input.close()
            self.midi_input = None
        if self.midi_output:
            self.midi_output.close()
            self.midi_output = None

        input_name = self.midi_input_var.get()
        output_name = self.midi_output_var.get()

        if input_name != "None" and input_name in mido.get_input_names():
            self.midi_input = mido.open_input(input_name, callback=self.on_midi_input)
        if output_name != "None" and output_name in mido.get_output_names():
            self.midi_output = mido.open_output(output_name)

        self.save_midi_ports()  # Save selected MIDI ports

    def on_key_click(self, event, key_id):
        self.canvas.itemconfig(key_id, fill="blue")
        self.indicator_color = "blue"  # Change indicator color to blue
        self.canvas.itemconfig(self.indicator_rect, fill=self.indicator_color)  # Change indicator rectangle to blue
        note, octave = self.get_note_and_octave_from_key_id(key_id)
        if note is not None:
            velocity = 127  # Set velocity to 127
            if 0 <= note <= 127 and 0 <= velocity <= 127:
                self.key_status_label.config(text=f"Key Pressed: {NOTE_NAMES[note % 12]}{octave}, Velocity: {velocity}")
                if self.midi_output:
                    self.start_time = time.time()  # Start time for round trip calculation
                    self.midi_output.send(mido.Message('note_on', note=note, velocity=velocity))
            self.active_keys[key_id] = note  # Ensure the key remains active

    def on_key_release(self, event, key_id):
        original_color = self.key_colors[key_id]  # Use key_colors to get the original color
        self.canvas.itemconfig(key_id, fill=original_color)
        self.indicator_color = "green"  # Change indicator color to green
        self.canvas.itemconfig(self.indicator_rect, fill=self.indicator_color)  # Change indicator rectangle to green
        note, _ = self.get_note_and_octave_from_key_id(key_id)
        if note is not None and 0 <= note <= 127:
            if self.midi_output:
                self.midi_output.send(mido.Message('note_off', note=note, velocity=0))  # Set velocity to 0
        self.active_keys[key_id] = None  # Deactivate the key

    def on_midi_input(self, message):
        
        if message.type == 'note_on' and message.velocity > 0:
            note_name = NOTE_NAMES[message.note % 12]
            octave = (message.note // 12) - 1
            velocity = message.velocity
            print(f"Incoming note_on: {note_name}{octave}, Velocity: {velocity}")  # Print the velocity to the terminal
            self.midi_status_label.config(text=f"MIDI Input: {note_name}{octave}, Velocity: {velocity}")
            if self.start_time:
                round_trip_time_s = time.time() - self.start_time  # Calculate time difference in seconds
                round_trip_time_ms = round_trip_time_s * 1000  # Convert to milliseconds
                self.round_trip_label.config(text=f"Round Trip Time: {round_trip_time_ms:.2f} ms")
                self.start_time = None  # Reset start time

    def get_note_and_octave_from_key_id(self, key_id):
        note = self.active_keys.get(key_id)
        if note is None:
            return None, None
        octave = (note // 12) - 1
        return note, octave
        return note, octave

if __name__ == "__main__":
    app = SynthesiaKeyboard()
    app.mainloop()
