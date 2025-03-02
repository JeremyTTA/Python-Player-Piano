import tkinter as tk
from tkinter import ttk
import mido
import time

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

class SynthesiaKeyboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Synthesia Style Keyboard")
        self.geometry("800x400")  # Initial window size
        self.bind("<Configure>", self.on_resize)

        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True, anchor=tk.SW)

        self.active_keys = {}
        self.key_colors = {}  # New dictionary to store original colors

        self.draw_keyboard()
        self.midi_output = None
        self.midi_input = None
        self.create_midi_controls()
        self.create_status_labels()

    def on_resize(self, event):
        self.canvas.delete("all")
        self.draw_keyboard()

    def draw_keyboard(self):
        width = self.winfo_width()
        height = self.winfo_height() // 4  # 1/4 of the window height (increased height)
        white_key_width = width / 52  # 52 white keys
        black_key_width = white_key_width * 2 / 3  # Black keys are narrower
        black_key_height = height * 3 / 5  # Black keys are shorter

        # Draw blue line above the keyboard
        self.canvas.create_line(0, self.winfo_height() - height - 2, width, self.winfo_height() - height - 2, fill="blue", width=4)

        # Draw white keys
        for i in range(52):
            x0 = i * white_key_width
            x1 = x0 + white_key_width
            y0 = self.winfo_height() - height
            y1 = self.winfo_height()
            key_id = self.canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="black")
            self.canvas.tag_bind(key_id, "<Button-1>", lambda e, k=key_id: self.on_key_click(e, k))
            self.canvas.tag_bind(key_id, "<ButtonRelease-1>", lambda e, k=key_id: self.on_key_release(e, k))
            self.canvas.tag_bind(key_id, "<Leave>", lambda e, k=key_id: self.on_key_leave(e, k))
            self.active_keys[key_id] = 21 + i  # Assign MIDI note number starting from 21
            self.key_colors[key_id] = "white"  # Store original color

        # Draw black keys
        black_key_positions = [1, 3, 4, 6, 7, 8]  # Corrected positions of black keys in an octave
        for octave in range(7):  # 7 full octaves
            for pos in black_key_positions:
                x0 = (octave * 7 + pos) * white_key_width - black_key_width / 2
                x1 = x0 + black_key_width
                y0 = self.winfo_height() - height
                y1 = y0 + black_key_height
                key_id = self.canvas.create_rectangle(x0, y0, x1, y1, fill="black", outline="white")
                self.canvas.tag_bind(key_id, "<Button-1>", lambda e, k=key_id: self.on_key_click(e, k))
                self.canvas.tag_bind(key_id, "<ButtonRelease-1>", lambda e, k=key_id: self.on_key_release(e, k))
                self.canvas.tag_bind(key_id, "<Leave>", lambda e, k=key_id: self.on_key_leave(e, k))
                self.active_keys[key_id] = 21 + 52 + (octave * 5) + black_key_positions.index(pos)  # Assign MIDI note number for black keys
                self.key_colors[key_id] = "black"  # Store original color

        # Draw the last black key in the 8th octave
        x0 = 7 * 7 * white_key_width + black_key_positions[0] * white_key_width - black_key_width / 2
        x1 = x0 + black_key_width
        y0 = self.winfo_height() - height
        y1 = y0 + black_key_height
        key_id = self.canvas.create_rectangle(x0, y0, x1, y1, fill="black", outline="white")
        self.canvas.tag_bind(key_id, "<Button-1>", lambda e, k=key_id: self.on_key_click(e, k))
        self.canvas.tag_bind(key_id, "<ButtonRelease-1>", lambda e, k=key_id: self.on_key_release(e, k))
        self.canvas.tag_bind(key_id, "<Leave>", lambda e, k=key_id: self.on_key_leave(e, k))
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
        self.midi_input_dropdown['values'] = mido.get_input_names()
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
        self.midi_output_dropdown['values'] = mido.get_output_names()
        self.midi_output_dropdown.grid(row=1, column=1, padx=5, pady=5)

        # MIDI Output Status Circle
        self.midi_output_status = tk.Canvas(control_frame, width=20, height=20, bg="black", highlightthickness=0)
        self.midi_output_status.create_oval(0, 0, 20, 20, fill="red")
        self.midi_output_status.grid(row=1, column=2, padx=5, pady=5)

        self.midi_input_var.trace("w", self.update_midi_ports)
        self.midi_output_var.trace("w", self.update_midi_ports)
        self.check_midi_status()

    def create_status_labels(self):
        status_frame = tk.Frame(self, bg="black")
        status_frame.place(relx=0.0, rely=0.0, x=10, y=70, anchor='nw')

        self.key_status_label = tk.Label(status_frame, text="Key Pressed: None", fg="white", bg="black")
        self.key_status_label.grid(row=0, column=0, padx=5, pady=5)

        self.midi_status_label = tk.Label(status_frame, text="MIDI Input: None", fg="white", bg="black")
        self.midi_status_label.grid(row=1, column=0, padx=5, pady=5)

        self.round_trip_label = tk.Label(status_frame, text="Round Trip Time: N/A", fg="white", bg="black")
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
        if self.midi_output:
            self.midi_output.close()

        input_name = self.midi_input_var.get()
        output_name = self.midi_output_var.get()

        if input_name in mido.get_input_names():
            self.midi_input = mido.open_input(input_name, callback=self.on_midi_input)
        if output_name in mido.get_output_names():
            self.midi_output = mido.open_output(output_name)

    def on_key_click(self, event, key_id):
        self.canvas.itemconfig(key_id, fill="blue")
        note, octave = self.get_note_and_octave_from_key_id(key_id)
        velocity = 127  # Set velocity to 127
        if 0 <= note <= 127 and 0 <= velocity <= 127:
            self.key_status_label.config(text=f"Key Pressed: {NOTE_NAMES[note % 12]}{octave}, Velocity: {velocity}")
            if self.midi_output:
                self.midi_output.send(mido.Message('note_on', note=note, velocity=velocity))

    def on_key_release(self, event, key_id):
        original_color = self.key_colors[key_id]  # Use key_colors to get the original color
        self.canvas.itemconfig(key_id, fill=original_color)
        note, _ = self.get_note_and_octave_from_key_id(key_id)
        if 0 <= note <= 127:
            if self.midi_output:
                self.midi_output.send(mido.Message('note_off', note=note))

    def on_midi_input(self, message):
        start_time = time.time_ns()
        if message.type == 'note_on' or message.type == 'note_off':
            self.midi_status_label.config(text=f"MIDI Input: {message.note}, Velocity: {message.velocity}")
            round_trip_time = time.time_ns() - start_time
            self.round_trip_label.config(text=f"Round Trip Time: {round_trip_time} ns")

    def get_note_and_octave_from_key_id(self, key_id):
        note = self.active_keys[key_id]
        octave = (note // 12) - 1
        return note, octave

    def on_key_leave(self, event, key_id):
        original_color = self.key_colors[key_id]  # Use key_colors to get the original color
        self.canvas.itemconfig(key_id, fill=original_color)
        note, _ = self.get_note_and_octave_from_key_id(key_id)
        if 0 <= note <= 127:
            if self.midi_output:
                self.midi_output.send(mido.Message('note_off', note=note))

if __name__ == "__main__":
    app = SynthesiaKeyboard()
    app.mainloop()
