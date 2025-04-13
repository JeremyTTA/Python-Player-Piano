import tkinter as tk
from tkinter import ttk
import mido
import time
import json  # Import json module
import csv  # Import csv module

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

class SynthesiaKeyboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Standlee Player Piano")
        self.geometry("800x400")  # Initial window size
        self.bind("<Configure>", self.on_resize)

        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True, anchor=tk.SW)
        
        # Wait for window to be ready
        self.update_idletasks()
        
        # Initialize table positions
        self.update_table_position()  # Remove table_height initialization

        self.active_keys = {}
        self.key_colors = {}  # New dictionary to store original colors
        self.pressed_keys = set()  # Add this to track currently pressed keys

        self.load_window_size()  # Load saved window size

        self.delay_ms = 50  # Initialize delay before creating controls

        self.mouse_pressed = False  # Add this line before draw_keyboard()
        self.bind("<ButtonRelease-1>", self.on_global_mouse_release)  # Add global mouse release handler
        self.draw_keyboard()
        self.midi_output = None
        self.midi_input = None
        self.create_note_table()  # Create table first
        self.create_midi_controls()
        self.create_status_labels()

        self.load_midi_ports()  # Load saved MIDI ports

        self.indicator_rect = None  # Initialize the indicator rectangle
        self.indicator_counter = 0  # Initialize the counter
        self.indicator_text = None  # Initialize the indicator text
        self.indicator_color = "green"  # Initialize the indicator color
        self.create_indicator_rect()  # Create the indicator rectangle

        self.start_time = None  # Initialize start time for round trip calculation

        self.midi_input_dropdown.bind('<<ComboboxSelected>>', self.update_midi_ports)
        self.midi_output_dropdown.bind('<<ComboboxSelected>>', self.update_midi_ports)
        # Start checking MIDI status immediately
        self.check_midi_status()

        self.is_playing = False
        self.current_key_index = 0
        self.sorted_keys = []
        self.delay_ms = 50  # Default delay

        # Add this after loading ports
        self.after(100, self.update_midi_ports)  # Auto-connect on startup

        # Add hover label with large font
        self.hover_label = tk.Label(self, 
                               text="Hover: None", 
                               fg="white", 
                               bg="black", 
                               font=('TkDefaultFont', 14, 'bold'))
        self.hover_label.place(relx=0.5, rely=0.02, anchor='n')

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
        self.update_table_position()

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
            # Add more robust mouse event handling
            self.canvas.tag_bind(key_id, "<ButtonPress-1>", lambda e, k=key_id: self.on_key_press(e, k))
            self.canvas.tag_bind(key_id, "<ButtonRelease-1>", lambda e, k=key_id: self.on_key_release(e, k))
            self.canvas.tag_bind(key_id, "<Enter>", lambda e, k=key_id: self.on_mouse_enter(e, k))
            self.canvas.tag_bind(key_id, "<Leave>", lambda e, k=key_id: self.on_mouse_leave(e, k))
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
            # Add more robust mouse event handling
            self.canvas.tag_bind(key_id, "<ButtonPress-1>", lambda e, k=key_id: self.on_key_press(e, k))
            self.canvas.tag_bind(key_id, "<ButtonRelease-1>", lambda e, k=key_id: self.on_key_release(e, k))
            self.canvas.tag_bind(key_id, "<Enter>", lambda e, k=key_id: self.on_mouse_enter(e, k))
            self.canvas.tag_bind(key_id, "<Leave>", lambda e, k=key_id: self.on_mouse_leave(e, k))
            self.active_keys[key_id] = note  # Assign MIDI note number
            self.key_colors[key_id] = "black"  # Store original color
            

        # Draw the last black key in the 8th octave
        x0 = 7 * 7 * white_key_width + black_key_positions[0] * white_key_width - black_key_width / 2
        x1 = x0 + black_key_width
        y0 = self.winfo_height() - height
        y1 = y0 + black_key_height
        key_id = self.canvas.create_rectangle(x0, y0, x1, y1, fill="black", outline="white")
        self.canvas.tag_bind(key_id, "<ButtonPress-1>", lambda e, k=key_id: self.on_key_press(e, k))
        self.canvas.tag_bind(key_id, "<ButtonRelease-1>", lambda e, k=key_id: self.on_key_release(e, k))
        self.canvas.tag_bind(key_id, "<Enter>", lambda e, k=key_id: self.on_mouse_enter(e, k))
        self.canvas.tag_bind(key_id, "<Leave>", lambda e, k=key_id: self.on_mouse_leave(e, k))
        self.active_keys[key_id] = 106  # Assign MIDI note number for the last black key
        self.key_colors[key_id] = "black"  # Store original color

    def create_midi_controls(self):
        control_frame = tk.Frame(self, bg="black")
        control_frame.place(relx=0.02, rely=0.02, anchor="nw")  # Adjusted positioning without padx/pady

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
        output_label.grid(row=1, column=0)

        # MIDI Output Dropdown
        self.midi_output_var = tk.StringVar()
        self.midi_output_dropdown = ttk.Combobox(control_frame, textvariable=self.midi_output_var)
        self.midi_output_dropdown['values'] = ["None"] + mido.get_output_names()
        self.midi_output_dropdown.grid(row=1, column=1, padx=5, pady=5)

        # MIDI Output Status Circle
        self.midi_output_status = tk.Canvas(control_frame, width=20, height=20, bg="black", highlightthickness=0)
        self.midi_output_status.create_oval(0, 0, 20, 20, fill="red")
        self.midi_output_status.grid(row=1, column=2, padx=5, pady=5)

        # Add delay input field with validation
        delay_label = tk.Label(control_frame, text="Delay (ms):", fg="white", bg="black")
        delay_label.grid(row=2, column=0)
        
        vcmd = (self.register(self.validate_delay), '%P')
        self.delay_entry = tk.Entry(control_frame, width=5, validate='key', validatecommand=vcmd)
        self.delay_entry.insert(0, str(self.delay_ms))
        self.delay_entry.grid(row=2, column=1, padx=0, pady=5)
        
        # Add test button next to calibrate
        self.test_button = tk.Button(control_frame, text="Test", command=self.simulate_first_key,
                              bg="gray", fg="black", width=10, font=('TkDefaultFont', 9, 'bold'))
        self.test_button.grid(row=2, column=4, padx=5, pady=5)

        # Add Clear button next to Test button
        self.clear_button = tk.Button(control_frame, text="Clear", command=self.clear_table,
                              bg="gray", fg="black", width=10, font=('TkDefaultFont', 9, 'bold'))
        self.clear_button.grid(row=2, column=5, padx=5, pady=5)  # Place after Test button

        # Add Note Off button next to Clear button
        self.note_off_button = tk.Button(control_frame, text="Note Off", command=self.send_all_notes_off,
                              bg="gray", fg="black", width=10, font=('TkDefaultFont', 9, 'bold'))
        self.note_off_button.grid(row=2, column=6, padx=5, pady=5)  # Place after Clear button

        # Add velocity slider after the delay controls
        velocity_frame = tk.Frame(control_frame, bg="black")
        velocity_frame.grid(row=3, column=0, columnspan=6, padx=5, pady=5, sticky='ew')
        
        velocity_label = tk.Label(velocity_frame, text="Velocity:", fg="white", bg="black", font=('TkDefaultFont', 12))
        velocity_label.pack(side=tk.LEFT, padx=5)
        
        self.velocity_value = tk.IntVar(value=100)  # Default to 100%
        self.velocity_slider = ttk.Scale(
            velocity_frame, 
            from_=0, 
            to=100,
            orient='horizontal',
            variable=self.velocity_value,
            length=200
        )
        self.velocity_slider.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Add percentage label that updates with slider
        self.velocity_percent = tk.Label(velocity_frame, text="100%", fg="white", bg="black", font=('TkDefaultFont', 12))
        self.velocity_percent.pack(side=tk.LEFT, padx=5)
        
        # Bind slider to update percentage label
        self.velocity_slider.bind('<Motion>', self.update_velocity_label)
        self.velocity_slider.bind('<ButtonRelease-1>', self.update_velocity_label)

    def validate_delay(self, value):
        if value == "": return True
        try:
            delay = int(value)
            return 0 <= delay <= 5000  # Allow delays between 0 and 5000ms
        except ValueError:
            return False

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
        status_frame = tk.Frame(self, height=100, bg="black")
        status_frame.place(relx=0.98, rely=0.02, anchor='ne')  # Changed from 0.50 to 0.98 and 'n' to 'ne'

        # Increased width and font size for better visibility
        label_font = ('TkDefaultFont', 12)
        label_width = 35

        self.key_status_label = tk.Label(status_frame, 
                                        text="Key Pressed: None", 
                                        fg="white", bg="black", 
                                        width=label_width, 
                                        anchor='e',  # Changed from 'w' to 'e' for right alignment
                                        wraplength=300,
                                        font=label_font)
        self.key_status_label.grid(row=0, column=0, padx=5, pady=5)

        self.midi_status_label = tk.Label(status_frame, 
                                        text="MIDI Input: None", 
                                        fg="white", bg="black", 
                                        width=label_width, 
                                        anchor='e',  # Changed from 'w' to 'e' for right alignment
                                        wraplength=300,
                                        font=label_font)
        self.midi_status_label.grid(row=1, column=0, padx=5, pady=5)

        self.round_trip_label = tk.Label(status_frame, 
                                        text="Round Trip Time: N/A", 
                                        fg="white", bg="black", 
                                        width=label_width, 
                                        anchor='e',  # Changed from 'w' to 'e' for right alignment
                                        wraplength=300,
                                        font=label_font)
        self.round_trip_label.grid(row=2, column=0, padx=5, pady=5)

    def check_midi_status(self): 
        input_name = self.midi_input_var.get()
        output_name = self.midi_output_var.get()        
        
        # Simplified connection checks
        input_connected = (input_name != "None" and input_name in mido.get_input_names() 
                         and self.midi_input is not None)
        output_connected = (output_name != "None" and output_name in mido.get_output_names() 
                          and self.midi_output is not None)

        self.midi_input_status.itemconfig(1, fill="green" if input_connected else "red")
        self.midi_output_status.itemconfig(1, fill="green" if output_connected else "red")

        self.after(1000, self.check_midi_status)

    def update_midi_ports(self, *args):
        print("\n=== MIDI Port Update ===")
        print(f"Available inputs: {mido.get_input_names()}")
        print(f"Available outputs: {mido.get_output_names()}")
        
        if self.midi_input:
            print(f"Closing existing input: {self.midi_input}")
            self.midi_input.close()
            self.midi_input = None
        if self.midi_output:
            print(f"Closing existing output: {self.midi_output}")
            self.midi_output.close()
            self.midi_output = None

        input_name = self.midi_input_var.get()
        output_name = self.midi_output_var.get()
        
        print(f"Attempting to connect to input: {input_name}")
        print(f"Attempting to connect to output: {output_name}")

        try:
            if input_name != "None" and input_name in mido.get_input_names():
                self.midi_input = mido.open_input(input_name, callback=self.on_midi_input)
                print(f"Successfully connected to input: {input_name}")
            if output_name != "None" and output_name in mido.get_output_names():
                self.midi_output = mido.open_output(output_name)
                print(f"Successfully connected to output: {output_name}")
        except Exception as e:
            print(f"Error connecting to MIDI ports: {str(e)}")

        self.save_midi_ports()
        self.check_midi_status()

    def on_key_click(self, event, key_id):
        self.canvas.itemconfig(key_id, fill="blue")
        self.indicator_color = "blue"  # Change indicator color to blue
        self.canvas.itemconfig(self.indicator_rect, fill=self.indicator_color)  # Change indicator rectangle to blue
        note = self.active_keys.get(key_id)
        if note is not None:
            velocity = self.get_velocity()  # Use slider value instead of fixed 127
            if 0 <= note <= 127 and 0 <= velocity <= 127:
                self.pressed_keys.add(key_id)  # Add key to pressed keys
                octave = (note // 12) - 1
                self.key_status_label.config(text=f"Key Pressed: {NOTE_NAMES[note % 12]}{octave}, Velocity: {velocity}")
                if self.midi_output:
                    self.start_time = time.time()  # Start time for round trip calculation
                    self.midi_output.send(mido.Message('note_on', note=note, velocity=velocity))
            
            self.active_keys[key_id] = note  # Ensure the key remains active
        self.refresh_window()  # Refresh the window

    def on_key_release(self, event, key_id):
        self.mouse_pressed = False
        # Rest of existing on_key_release code...
        if key_id in self.pressed_keys:  # Only process if key was actually pressed
            self.pressed_keys.remove(key_id)
            original_color = self.key_colors[key_id]  # Use key_colors to get the original color
            self.canvas.itemconfig(key_id, fill=original_color)
            self.indicator_color = "green"  # Change indicator color to green
            self.canvas.itemconfig(self.indicator_rect, fill=self.indicator_color)  # Change indicator rectangle to green
            note = self.active_keys.get(key_id)
          
            if note is not None and 0 <= note <= 127:
                if self.midi_output:
                    self.midi_output.send(mido.Message('note_off', note=note, velocity=0))  # Set velocity to 0
            self.active_keys[key_id] = note  # Ensure the key remains active
 

    def on_midi_input(self, message):
        if message.type == 'note_on' and message.velocity > 0:
            note_name = NOTE_NAMES[message.note % 12]
            octave = (message.note // 12) - 1
            velocity = message.velocity
            self.midi_status_label.config(text=f"MIDI Input: {note_name}{octave}, Velocity: {velocity}")
            if self.start_time:
                round_trip_time_s = time.time() - self.start_time  # Calculate time difference in seconds
                round_trip_time_ms = round_trip_time_s * 1000  # Convert to milliseconds
                self.round_trip_label.config(text=f"Round Trip Time: {round_trip_time_ms:.2f} ms")
                self.update_note_table(message.note, message.velocity, round_trip_time_ms)  # Update the table
                self.start_time = None  # Reset start time
        elif message.type == 'note_off' or (message.type == 'note_on' and message.velocity == 0):
            note_name = NOTE_NAMES[message.note % 12]
            octave = (message.note // 12) - 1
        
    def get_note_and_octave_from_key_id(self, key_id):
        note = self.active_keys.get(key_id)
        print(key_id)
        print(self.active_keys.get(key_id))  # Corrected syntax
        if note is None:
            return None, None
        octave = (note // 12) - 1
        return note, octave

    def refresh_window(self):
        self.update_idletasks()

    def create_note_table(self):
        self.table_frame = tk.Frame(self, bg="grey", relief="raised", borderwidth=1)
        self.update_table_position()

        # Increase columns and adjust rows per column
        num_columns = 8  # Increased from 6 to 8
        rows_per_column = 11  # Adjusted from 15 to 11 to fit all 88 keys

        # Configure grid columns to be equal with increased width
        for i in range(num_columns):
            self.table_frame.grid_columnconfigure(i, weight=1, minsize=150)  # Increased from 130 to 150

        # Header labels with larger font
        header_text = "Note|MIDI|V|RT"
        for col in range(num_columns):
            header = tk.Label(self.table_frame, text=header_text,
                             fg="black", bg="grey", anchor='w',
                             font=("TkDefaultFont", 12, 'bold'))  # Increased from 8 to 12
            header.grid(row=0, column=col, sticky='w', padx=3, pady=2)  # Slightly increased padding

        # Create note rows with larger font
        self.note_list_rows = []
        for i in range(88):
            midi_note = i + 21
            note_name = NOTE_NAMES[midi_note % 12]
            octave = (midi_note // 12) - 1
            
            row_frame = tk.Frame(self.table_frame, bg="black")
            row_frame.grid(row=i % rows_per_column + 1, column=i // rows_per_column, 
                          sticky='w', padx=3, pady=1)
            
            # Note name in bold blue
            note_label = tk.Label(row_frame, text=f"{note_name}{octave}", 
                                fg="blue", bg="grey", 
                                font=("TkDefaultFont", 12, "bold"))  # Increased from 8 to 12
            note_label.pack(side=tk.LEFT)
            
            # Separator
            tk.Label(row_frame, text="|", fg="black", bg="grey",
                    font=("TkDefaultFont", 12)).pack(side=tk.LEFT)  # Increased from 8 to 12
            
            # MIDI note in red
            midi_label = tk.Label(row_frame, text=str(midi_note),
                                fg="red", bg="grey",
                                font=("TkDefaultFont", 12))  # Increased from 8 to 12
            midi_label.pack(side=tk.LEFT)
            
            # Values section in white
            values_label = tk.Label(row_frame, text="|--|--",
                                  fg="white", bg="grey",
                                  font=("TkDefaultFont", 12))  # Increased from 8 to 12
            values_label.pack(side=tk.LEFT)
            
            self.note_list_rows.append((note_label, midi_label, values_label))

    def update_table_position(self):
        """Recalculate and update table position"""
        if hasattr(self, 'table_frame'):
            keyboard_height = self.winfo_height() // 4
            control_height = 150  # Approximate height of control frame
            
            # Calculate position and height
            y_pos = control_height
            table_height = self.winfo_height() - keyboard_height - control_height - 4
            
            self.table_frame.place(x=0, y=y_pos, relwidth=1.0, height=table_height)

    def update_note_table(self, note, velocity, return_time=None):
        # Calculate the index for the note (A0 = MIDI 21, so index = note - 21)
        index = note - 21
        if 0 <= index < 88:
            note_name = NOTE_NAMES[note % 12]
            octave = (note // 12) - 1
            return_time_text = f"{return_time:.1f}" if return_time is not None else "N/A"  # Shortened decimal
            
            # Update each part with appropriate styling
            note_label, midi_label, values_label = self.note_list_rows[index]
            values_label.config(text=f"|{velocity}|{return_time_text}")
            
            # Change text color to red if roundtrip time exceeds 100ms, otherwise white
            if return_time is not None:
                text_color = "black" if return_time > 75 else "white"
                values_label.config(fg=text_color)

    def simulate_first_key(self):
        # Get delay from entry field
        try:
            self.delay_ms = int(self.delay_entry.get())
        except ValueError:
            print("Invalid delay value, using default 50ms")
            self.delay_ms = 50
            self.delay_entry.delete(0, tk.END)
            self.delay_entry.insert(0, str(self.delay_ms))
            
        # Create a sorted list of MIDI notes and find their corresponding key_ids
        self.midi_notes = sorted(list(set(self.active_keys.values())))  # Get unique sorted MIDI notes
        self.key_id_map = {note: key_id for key_id, note in self.active_keys.items()}  # Map notes to key_ids
        self.current_test_index = 0
        
        print(f"Starting test sequence with {len(self.midi_notes)} notes")
        # Disable test button during playback
        self.test_button.config(state="disabled")
        self.test_next_key()

    def test_next_key(self):
        if self.current_test_index >= len(self.midi_notes):
            print("Finished testing all keys")
            self.test_button.config(state="normal")
            return
            
        note = self.midi_notes[self.current_test_index]
        key_id = self.key_id_map[note]
        mock_event = type('Event', (), {'x': 0, 'y': 0})()
        
        # Use existing key press logic
        self.on_key_click(mock_event, key_id)
        
        # Schedule release after delay
        self.after(self.delay_ms, lambda: self.release_key_and_continue(mock_event, key_id))

    def release_key_and_continue(self, event, key_id):
        """Handle key release and schedule next key"""
        # Use existing release logic
        self.on_key_release(event, key_id)
        
        # Wait for full delay before next key
        self.current_test_index += 1
        self.after(self.delay_ms, self.test_next_key)

    def on_key_press(self, event, key_id):
        """Modified to prevent duplicate presses"""
        if not self.mouse_pressed:  # Only process if not already pressed
            self.mouse_pressed = True
            self.on_key_click(event, key_id)

    def on_mouse_enter(self, event, key_id):
        note = self.active_keys.get(key_id)
        self.update_hover_label(note)
        if self.mouse_pressed and key_id not in self.pressed_keys:
            self.on_key_click(event, key_id)

    def on_mouse_leave(self, event, key_id):
        # Reset highlight when mouse leaves any key
        for note_label, midi_label, values_label in self.note_list_rows:
            note_label.config(bg="grey")
            midi_label.config(bg="grey")
            values_label.config(bg="grey")
        
        self.update_hover_label(None)
        if key_id in self.pressed_keys:
            self.on_key_release(event, key_id)

    def on_global_mouse_release(self, event):
        """Handle mouse release anywhere in window"""
        if self.mouse_pressed:
            self.mouse_pressed = False
            # Release all pressed keys
            for key_id in list(self.pressed_keys):  # Use list to avoid modifying set during iteration
                self.on_key_release(event, key_id)

    def clear_table(self):
        """Clear all values in the note table"""
        for _, _, values_label in self.note_list_rows:
            values_label.config(text="|--|--", fg="white")  # Reset text and color
        
        # Reset status labels
        self.key_status_label.config(text="Key Pressed: None")
        self.midi_status_label.config(text="MIDI Input: None")
        self.round_trip_label.config(text="Round Trip Time: N/A")

    def update_velocity_label(self, event=None):
        value = self.velocity_value.get()
        self.velocity_percent.config(text=f"{value}%")

    def get_velocity(self):
        """Convert percentage to MIDI velocity (0-127)"""
        return int((self.velocity_value.get() / 100) * 127)

    def send_all_notes_off(self):
        """Send note-off messages for all possible MIDI notes"""
        if self.midi_output:
            for note in range(21, 109):  # MIDI notes from A0 (21) to C8 (108)
                self.midi_output.send(mido.Message('note_off', note=note, velocity=0))
            print("All notes off sent")

    def update_hover_label(self, note):
        # Reset previous highlight if any
        for _, _, values_label in self.note_list_rows:
            values_label.config(bg="grey")  # Reset all backgrounds to default
            
        if note is None:
            self.hover_label.config(text="Hover: None")
        else:
            note_name = NOTE_NAMES[note % 12]
            octave = (note // 12) - 1
            self.hover_label.config(text=f"Hover: {note_name}{octave} ({note})")
            
            # Highlight the corresponding table row
            index = note - 21  # Convert MIDI note to table index
            if 0 <= index < 88:
                note_label, midi_label, values_label = self.note_list_rows[index]
                # Highlight the entire row
                note_label.config(bg="#404040")  # Darker grey for highlight
                midi_label.config(bg="#404040")
                values_label.config(bg="#404040")

if __name__ == "__main__":
    app = SynthesiaKeyboard()
    app.mainloop()
