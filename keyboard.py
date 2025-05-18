import tkinter as tk
from tkinter import ttk, filedialog  # Add filedialog import
import mido
import time
import json  # Import json module
import csv  # Import csv module
import os  # Add os import for path handling

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

class SynthesiaKeyboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Standlee Player Piano")
        
        # Initialize MIDI variables first
        self.midi_input = None
        self.midi_output = None
        
        # Default size if no saved state
        self.geometry("800x400")
        self.state('normal')  # Ensure window starts in normal state
        
        # Create tabs first so they're at the bottom of the z-order
        self.create_tabs()
        
        # Create MIDI visualization
        self.create_midi_visualization()
        
        # Load window size and state before creating other elements
        self.load_window_size()

        self.bind("<Configure>", self.on_resize)

        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True, anchor=tk.SW)
        
        # Wait for window to be ready
        self.update_idletasks()
        
        # Initialize table positions
        self.update_table_position()

        self.active_keys = {}
        self.key_colors = {}
        self.pressed_keys = set()

        self.delay_ms = 50

        self.mouse_pressed = False
        self.bind("<ButtonRelease-1>", self.on_global_mouse_release)
        self.draw_keyboard()
        self.midi_output = None
        self.midi_input = None

        # Create remaining UI elements
        self.create_note_table()
        self.create_midi_controls()
        self.create_status_labels()

        # Initialize button visibility based on current tab
        self.update_button_visibility()

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

        self.midi_file = None
        self.midi_messages = []  # Store parsed MIDI messages
        self.is_playing = False
        self.playback_index = 0
        self.last_message_time = 0

        # Start MIDI callback after initialization
        self.start_midi_callback()
        
        # Refresh MIDI ports periodically
        self.after(5000, self.periodic_port_refresh)

    def create_tabs(self):
        """Create tabbed interface"""
        self.tab_control = ttk.Notebook(self)
        
        # Create MIDI File tab
        self.midi_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.midi_tab, text='MIDI File')
        
        # Create Calibrate tab
        self.calibrate_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.calibrate_tab, text='Calibrate')
        
        # Position tabs - lift above canvas but below controls
        keyboard_height = self.winfo_height() // 4
        control_height = 150
        self.tab_control.place(x=0, y=control_height, 
                             relwidth=1.0, 
                             height=self.winfo_height() - keyboard_height - control_height - 4)
        
        # Bind tab change to save settings and update button visibility
        self.tab_control.bind('<<NotebookTabChanged>>', self.on_tab_changed)

    def on_tab_changed(self, event):
        """Handle tab change events"""
        self.save_window_size()
        self.update_button_visibility()

    def update_button_visibility(self):
        """Update visibility of Test and Clear buttons based on current tab"""
        if not hasattr(self, 'test_button') or not hasattr(self, 'clear_button'):
            return
            
        current_tab = self.tab_control.select()
        is_calibrate_tab = current_tab == self.tab_control.tabs()[1]  # Check if Calibrate tab is selected
        
        if is_calibrate_tab:
            self.test_button.grid()  # Show buttons
            self.clear_button.grid()
        else:
            self.test_button.grid_remove()  # Hide buttons but preserve their space
            self.clear_button.grid_remove()

    def create_indicator_rect(self):
        self.indicator_counter += 1
        width = self.winfo_width()
        height = self.winfo_height()
        rect_size = 40  # Size of the rectangle
        x0 = (width - rect_size) // 2
        y0 = (height - rect_size) // 2
        x1 = x0 + rect_size
        y1 = y0 + rect_size  # Fixed: Add y1 calculation
        
        if self.indicator_rect:
            self.canvas.coords(self.indicator_rect, x0, y0, x1, y1)
            self.canvas.itemconfig(self.indicator_rect, fill=self.indicator_color)
        else:
            self.indicator_rect = self.canvas.create_rectangle(x0, y0, x1, y1, fill=self.indicator_color, outline="white")

    def on_resize(self, event):
        """Handle window resize with better state preservation"""
        if not self.winfo_viewable():  # Skip first resize event
            return
            
        # Store current visualization state if it exists
        had_visualization = hasattr(self, 'midi_messages') and self.midi_messages
        current_scroll = None
        if had_visualization:
            current_scroll = self.viz_canvas.yview()
            
        # Update window state
        self.save_window_size()
        
        # Redraw keyboard
        self.canvas.delete("all")
        self.draw_keyboard()
        self.create_indicator_rect()
        
        # Update other elements
        self.update_table_position()
        if hasattr(self, 'tab_control'):
            keyboard_height = self.winfo_height() // 4
            control_height = 150
            self.tab_control.place(x=0, y=control_height,
                                 relwidth=1.0,
                                 height=self.winfo_height() - keyboard_height - control_height - 4)
            self.tab_control.lift()
        
        # Restore visualization if it existed
        if had_visualization:
            self.after(100, lambda: self.restore_visualization(current_scroll))

    def restore_visualization(self, scroll_position=None):
        """Restore visualization with proper scroll position"""
        self.visualize_midi_file()
        if scroll_position:
            self.viz_canvas.yview_moveto(scroll_position[0])

    def save_window_size(self):
        size = {
            "width": self.winfo_width(),
            "height": self.winfo_height(),
            "last_tab": self.tab_control.select(),
            "state": self.state(),  # Save current window state
            "zoomed": self.wm_state() == 'zoomed'  # Explicitly track zoomed state
        }
        with open("window_size.json", "w") as f:
            json.dump(size, f)

    def load_window_size(self):
        try:
            with open("window_size.json", "r") as f:
                size = json.load(f)
                
                # Set initial geometry
                self.geometry(f'{size["width"]}x{size["height"]}')
                
                # Restore window state
                if size.get("zoomed", False):
                    self.state('zoomed')
                elif "state" in size:
                    self.state(size["state"])
                
                # Update tab selection
                if "last_tab" in size:
                    self.after(100, lambda: self.tab_control.select(size["last_tab"]))
                    
        except FileNotFoundError:
            # Use default size if no saved state
            self.geometry("800x400")
            self.state('normal')

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

        # Add Load MIDI button before Clear button
        self.load_midi_button = tk.Button(control_frame, text="Load MIDI", 
                                        command=self.load_midi_file,
                                        bg="gray", fg="black", width=10, 
                                        font=('TkDefaultFont', 9, 'bold'))
        self.load_midi_button.grid(row=2, column=5, padx=5, pady=5)

        # Adjust Clear button position
        self.clear_button = tk.Button(control_frame, text="Clear", command=self.clear_table,
                              bg="gray", fg="black", width=10, font=('TkDefaultFont', 9, 'bold'))
        self.clear_button.grid(row=2, column=6, padx=5, pady=5)  # Place after Test button

        # Adjust Note Off button position
        self.note_off_button = tk.Button(control_frame, text="Note Off", command=self.send_all_notes_off,
                              bg="gray", fg="black", width=10, font=('TkDefaultFont', 9, 'bold'))
        self.note_off_button.grid(row=2, column=7, padx=5, pady=5)  # Place after Clear button

        # Add MIDI file status label
        self.midi_file_label = tk.Label(control_frame, text="No MIDI file loaded",
                                      fg="white", bg="black",
                                      font=('TkDefaultFont', 9))
        self.midi_file_label.grid(row=4, column=0, columnspan=8, padx=5, pady=5)

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

        # Add playback controls frame
        playback_frame = tk.Frame(control_frame, bg="black")
        playback_frame.grid(row=5, column=0, columnspan=8, padx=5, pady=5)
        
        self.play_button = tk.Button(playback_frame, text="Play", 
                                   command=self.toggle_playback,
                                   bg="gray", fg="black", width=10,
                                   font=('TkDefaultFont', 9, 'bold'),
                                   state='disabled')
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(playback_frame, text="Stop", 
                                   command=self.stop_playback,
                                   bg="gray", fg="black", width=10,
                                   font=('TkDefaultFont', 9, 'bold'),
                                   state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)

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
        try:
            with open("midi_ports.json", "w") as f:
                json.dump(ports, f)
                print(f"Saved MIDI port settings: {ports}")
        except Exception as e:
            print(f"Error saving MIDI ports: {str(e)}")

    def load_midi_ports(self):
        try:
            with open("midi_ports.json", "r") as f:
                ports = json.load(f)
                print(f"Loading saved MIDI ports: {ports}")
                if "input" in ports:
                    self.midi_input_var.set(ports["input"])
                    print(f"Set input to: {ports['input']}")
                if "output" in ports:
                    self.midi_output_var.set(ports["output"])
                    print(f"Set output to: {ports['output']}")
        except FileNotFoundError:
            print("No saved MIDI port settings found")
        except Exception as e:
            print(f"Error loading MIDI ports: {str(e)}")

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
        """Update the display of MIDI connection status"""
        input_status = self.midi_input.name if self.midi_input else "Not Connected"
        output_status = self.midi_output.name if self.midi_output else "Not Connected"
        
        print(f"Input Status: {input_status}")
        print(f"Output Status: {output_status}")
        
        # Update status labels if they exist
        if hasattr(self, 'input_status_label'):
            self.input_status_label.config(text=f"Input: {input_status}")
        if hasattr(self, 'output_status_label'):
            self.output_status_label.config(text=f"Output: {output_status}")

    def update_midi_ports(self, event=None):
        """Update MIDI port connections based on dropdown selections"""
        try:
            # Get selected ports from dropdowns
            input_port = self.midi_input_var.get()
            output_port = self.midi_output_var.get()
            
            # Handle input port
            if hasattr(self, 'midi_input') and self.midi_input:
                self.midi_input.close()
                self.midi_input = None
            
            if input_port and input_port != "None":
                try:
                    self.midi_input = mido.open_input(input_port)
                    self.midi_input_status.create_oval(0, 0, 20, 20, fill="green")
                except Exception as e:
                    print(f"Error connecting to input port: {e}")
                    self.midi_input_status.create_oval(0, 0, 20, 20, fill="red")
            else:
                self.midi_input_status.create_oval(0, 0, 20, 20, fill="red")
            
            # Handle output port
            if hasattr(self, 'midi_output') and self.midi_output:
                self.midi_output.close()
                self.midi_output = None
                
            if output_port and output_port != "None":
                try:
                    self.midi_output = mido.open_output(output_port)
                    self.midi_output_status.create_oval(0, 0, 20, 20, fill="green")
                except Exception as e:
                    print(f"Error connecting to output port: {e}")
                    self.midi_output_status.create_oval(0, 0, 20, 20, fill="red")
            else:
                self.midi_output_status.create_oval(0, 0, 20, 20, fill="red")
            
            # Save port settings
            self.save_midi_ports()
            
            # Update status display
            self.check_midi_status()
            
        except Exception as e:
            print(f"Error updating MIDI ports: {e}")
            self.midi_input_status.create_oval(0, 0, 20, 20, fill="red")
            self.midi_output_status.create_oval(0, 0, 20, 20, fill="red")

    def connect_midi_input(self, port_name):
        """Connect to the selected MIDI input port"""
        try:
            # Close existing connection if any
            if self.midi_input:
                self.midi_input.close()
            
            # Open new connection
            self.midi_input = mido.open_input(port_name)
            self.input_var.set(port_name)  # Update dropdown display
            print(f"Connected to MIDI input: {port_name}")
            
            # Update status display
            self.check_midi_status()
        except Exception as e:
            print(f"Error connecting to MIDI input: {e}")
            self.input_var.set("Connection Failed")
            self.midi_input = None

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
        """Create note table inside a fixed tab with optimized drawing"""
        num_columns = 9
        
        # Create main frame
        self.table_frame = tk.Frame(self.calibrate_tab, bg="grey", relief="raised", borderwidth=1)
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Configure grid columns to be equal width
        for i in range(num_columns):
            self.table_frame.grid_columnconfigure(i, weight=1)
            
        # Cache fonts for reuse
        header_font = ("TkDefaultFont", 12, 'bold')
        row_font = ("TkDefaultFont", 12)
        
        # Header labels - single row with all headers
        header_text = "Note|MIDI|V|RT"
        for col in range(num_columns):
            header = tk.Label(self.table_frame, text=header_text,
                            fg="black", bg="grey", anchor='w',
                            font=header_font)
            header.grid(row=0, column=col, sticky='w', padx=3, pady=2)

        # Calculate rows per column
        total_keys = 88
        rows_per_column = (total_keys + num_columns - 1) // num_columns

        # Create note rows more efficiently
        self.note_list_rows = []
        for i in range(88):
            midi_note = i + 21
            note_name = NOTE_NAMES[midi_note % 12]
            octave = (midi_note // 12) - 1
            
            col = i // rows_per_column
            row = i % rows_per_column + 1
            
            # Create a single label for the entire row with formatted text
            row_text = f"{note_name}{octave}|{midi_note}|--|--"
            row_label = tk.Label(self.table_frame, 
                               text=row_text,
                               fg="white", 
                               bg="grey",
                               font=row_font,
                               anchor='w',
                               padx=3)
            row_label.grid(row=row, column=col, sticky='w', pady=1)
            
            # Store reference with note data
            self.note_list_rows.append({
                'label': row_label,
                'note': midi_note,
                'note_name': f"{note_name}{octave}"
            })

    def update_table_position(self):
        """Table now goes inside Calibrate tab"""
        if hasattr(self, 'table_frame'):
            self.table_frame.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)

    def update_note_table(self, note, velocity, return_time=None):
        """Update table row more efficiently"""
        index = note - 21
        if 0 <= index < 88:
            row_data = self.note_list_rows[index]
            return_time_text = f"{return_time:.1f}" if return_time is not None else "--"
            
            # Update text in single operation
            row_text = f"{row_data['note_name']}|{note}|{velocity}|{return_time_text}"
            row_data['label'].config(
                text=row_text,
                fg="black" if return_time and return_time > 75 else "white"
            )

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
        """More efficient hover highlighting"""
        if note is None:
            self.hover_label.config(text="Hover: None")
            # Reset last highlighted row if exists
            if hasattr(self, '_last_highlight') and self._last_highlight is not None:
                self.note_list_rows[self._last_highlight]['label'].config(bg="grey")
                self._last_highlight = None
        else:
            note_name = NOTE_NAMES[note % 12]
            octave = (note // 12) - 1
            self.hover_label.config(text=f"Hover: {note_name}{octave} ({note})")
            
            # Update highlight
            index = note - 21
            if 0 <= index < 88:
                # Reset previous highlight if exists
                if hasattr(self, '_last_highlight') and self._last_highlight is not None:
                    self.note_list_rows[self._last_highlight]['label'].config(bg="grey")
                
                # Set new highlight
                self.note_list_rows[index]['label'].config(bg="#404040")
                self._last_highlight = index

    def load_midi_file(self):
        """Open file dialog and load a MIDI file"""
        filepath = filedialog.askopenfilename(
            title="Select MIDI File",
            filetypes=[("MIDI files", "*.mid"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                # Clear previous visualization first
                self.clear_visualization()
                self.midi_messages = []
                
                # Update UI to show loading state
                self.midi_file_label.config(text="Loading MIDI file...")
                self.play_button.config(state='disabled')
                self.stop_button.config(state='disabled')
                
                # Initialize loading state
                self.midi_file = mido.MidiFile(filepath)
                self.loading_cancelled = False
                
                # Start asynchronous loading process
                self.after(10, lambda: self.process_midi_messages(filepath))
                
            except Exception as e:
                self.midi_file = None
                self.midi_file_label.config(text=f"Error loading file: {str(e)}")
                self.play_button.config(state='disabled')
                self.stop_button.config(state='disabled')

    def process_midi_messages(self, filepath, chunk_start=0):
        """Process MIDI messages in chunks to avoid hanging"""
        try:
            chunk_size = 1000  # Number of messages to process per chunk
            messages_processed = 0
            current_time = 0
            
            # Process a chunk of messages from each track
            for track_idx, track in enumerate(self.midi_file.tracks[chunk_start:]):
                track_time = 0
                
                for msg in track:
                    track_time += msg.time
                    if msg.type in ['note_on', 'note_off']:
                        self.midi_messages.append((track_time, msg))
                    
                    messages_processed += 1
                    if messages_processed >= chunk_size:
                        # Schedule next chunk and update progress
                        next_chunk = chunk_start + track_idx + 1
                        progress = f"Loading: {os.path.basename(filepath)}\nProcessed {len(self.midi_messages)} messages..."
                        self.midi_file_label.config(text=progress)
                        self.update_idletasks()
                        
                        self.after(1, lambda: self.process_midi_messages(filepath, next_chunk))
                        return
            
            # All messages processed, finish up
            self.finish_midi_loading(filepath)
            
        except Exception as e:
            self.midi_file_label.config(text=f"Error processing file: {str(e)}")
            self.play_button.config(state='disabled')
            self.stop_button.config(state='disabled')

    def finish_midi_loading(self, filepath):
        """Complete MIDI file loading and create visualization"""
        try:
            # Sort messages by time
            self.midi_messages.sort(key=lambda x: x[0])
            
            # Calculate total duration
            if self.midi_messages:
                duration = self.midi_messages[-1][0]
            else:
                duration = 0
            
            # Update UI
            self.midi_file_label.config(
                text=f"Loaded: {os.path.basename(filepath)}\n"
                     f"Messages: {len(self.midi_messages)}\n"
                     f"Duration: {duration:.1f}s"
            )
            
            # Enable playback controls
            self.play_button.config(state='normal')
            self.stop_button.config(state='normal')
            
            # Start visualization process
            self.create_visualization_in_chunks()
            
        except Exception as e:
            self.midi_file_label.config(text=f"Error finalizing file: {str(e)}")
            self.play_button.config(state='disabled')
            self.stop_button.config(state='disabled')

    def create_visualization_in_chunks(self, start_idx=0):
        """Create visualization incrementally to avoid hanging"""
        if not self.midi_messages:
            return
            
        try:
            # Switch to MIDI File tab and ensure canvas is ready
            self.tab_control.select(0)
            
            # First time setup
            if start_idx == 0:
                self.clear_visualization()
                max_time = self.midi_messages[-1][0]
                self.max_height = max_time * self.pixels_per_second + 50
                self.draw_measure_lines()
                self.update_idletasks()
            
            # Process a chunk of messages
            chunk_size = 100
            end_idx = min(start_idx + chunk_size, len(self.midi_messages))
            
            # Create note rectangles for this chunk
            active_notes = {}
            for time, msg in self.midi_messages[start_idx:end_idx]:
                if msg.type == 'note_on' and msg.velocity > 0:
                    active_notes[msg.note] = (time, msg.velocity)
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in active_notes:
                        start_time, velocity = active_notes[msg.note]
                        duration = time - start_time
                        if duration > 0:
                            self.add_note_visualization(msg.note, start_time, duration, velocity)
                        del active_notes[msg.note]
            
            # Update progress
            progress = f"{int((end_idx / len(self.midi_messages)) * 100)}% visualized..."
            self.midi_file_label.config(text=self.midi_file_label.cget("text") + f"\n{progress}")
            
            # Schedule next chunk if needed
            if end_idx < len(self.midi_messages):
                self.after(1, lambda: self.create_visualization_in_chunks(end_idx))
            else:
                # Finish up
                self.viz_canvas.configure(scrollregion=(0, 0, self.viz_canvas.winfo_width(), self.max_height))
                self.viz_canvas.yview_moveto(0.0)
                self.update_idletasks()
                
                # Remove progress message
                current_text = self.midi_file_label.cget("text")
                self.midi_file_label.config(text=current_text.split('\n', 3)[0:3])
                
        except Exception as e:
            self.midi_file_label.config(text=f"Error creating visualization: {str(e)}")

    def visualize_midi_file(self):
        """Start the chunked visualization process"""
        if not self.midi_messages:
            return
        self.create_visualization_in_chunks()

    def create_midi_visualization(self):
        """Create visualization area in MIDI File tab"""
        # Create container frame that fills the tab
        self.viz_container = tk.Frame(self.midi_tab)
        self.viz_container.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas with scrollbar
        self.viz_canvas = tk.Canvas(self.viz_container, bg="black", width=800, height=600)
        self.viz_scrollbar = ttk.Scrollbar(self.viz_container, orient="vertical", command=self.viz_canvas.yview)
        
        # Configure canvas
        self.viz_canvas.configure(yscrollcommand=self.viz_scrollbar.set)
        
        # Pack scrollbar and canvas
        self.viz_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.viz_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Force initial canvas update
        self.viz_container.update_idletasks()
        self.update_idletasks()
        
        # Set visualization parameters
        self.note_width = 15  # Fixed width for all note rectangles
        self.pixels_per_second = 50  # Vertical scale for duration
        self.max_height = 0  # Track maximum height for scroll region
        
        # Create tooltip
        self.tooltip = tk.Label(self, 
                              bg='black', 
                              fg='white',
                              font=('TkDefaultFont', 10),
                              relief='solid',
                              borderwidth=1)
        
        # Bind events
        self.viz_canvas.bind('<Motion>', self.update_tooltip)
        self.viz_canvas.bind('<Leave>', self.hide_tooltip)
        self.viz_canvas.bind('<MouseWheel>', lambda e: self.viz_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.viz_canvas.bind('<Configure>', self.on_viz_canvas_resize)

    def update_tooltip(self, event):
        """Update tooltip position and text based on mouse position"""
        # Convert mouse coordinates to canvas coordinates
        canvas_x = self.viz_canvas.canvasx(event.x)
        canvas_y = self.viz_canvas.canvasy(event.y)
        
        # Find items under cursor using coordinates
        items = self.viz_canvas.find_overlapping(canvas_x, canvas_y, canvas_x, canvas_y)
        
        if not items:
            self.hide_tooltip(None)
            return
            
        # Get the first item's tags
        tags = self.viz_canvas.gettags(items[0])
        
        # Check if it's a note rectangle
        for tag in tags:
            if tag.startswith('note:'):
                # Parse note info from tag
                _, note_name, velocity, duration = tag.split(':')
                
                # Create tooltip text
                tooltip_text = f"Note: {note_name}\nVelocity: {velocity}\nDuration: {float(duration):.1f}ms"
                
                # Update tooltip
                self.tooltip.config(text=tooltip_text)
                
                # Get absolute screen coordinates for tooltip
                x = self.winfo_rootx() + event.x + 10
                y = self.winfo_rooty() + event.y + 10
                
                # Show tooltip
                self.tooltip.place(x=x, y=y)
                return
                
        # Hide tooltip if no note found
        self.hide_tooltip(None)

    def hide_tooltip(self, event):
        """Hide the tooltip"""
        self.tooltip.place_forget()

    def add_note_visualization(self, note, start_time, duration, velocity):
        """Add a note rectangle to the visualization"""
        try:
            # Get x position
            note_x = self.get_note_x_position(note)
            if note_x is None:
                return None

            # Create note name
            note_name = NOTE_NAMES[note % 12] + str((note // 12) - 1)
            
            # Calculate y position and height with reduced scaling
            y_pos = start_time * self.pixels_per_second
            height = duration * 0.5  # Reduced from 5 to 0.5 pixels per second
            
            if height < 1:  # Ensure minimum height
                height = 1
            
            # Invert y position for reversed order
            y_pos = self.max_height - y_pos - height
            
            # Draw the note rectangle
            rect_id = self.viz_canvas.create_rectangle(
                note_x, y_pos,
                note_x + self.note_width, y_pos + height,
                fill=self.get_note_color(velocity),
                outline="white",
                tags=(f"note:{note_name}:{velocity}:{duration*1000:.1f}",)
            )
            
            # Add note name label if height is sufficient
            if height > 20:
                self.viz_canvas.create_text(
                    note_x + self.note_width/2, y_pos + height/2,
                    text=note_name,
                    fill="white",
                    angle=90
                )
            
            return rect_id
            
        except Exception as e:
            print(f"Error drawing note {note}: {str(e)}")
            return None

    def draw_measure_lines(self):
        """Draw horizontal lines for each measure based on time signature"""
        if not hasattr(self, 'midi_file') or not self.midi_file:
            return
            
        # Default to 4/4 time signature if not specified
        ticks_per_beat = self.midi_file.ticks_per_beat
        time_sig_numerator = 4
        time_sig_denominator = 4
        
        # Look for time signature message
        for track in self.midi_file.tracks:
            for msg in track:
                if msg.type == 'time_signature':
                    time_sig_numerator = msg.numerator
                    time_sig_denominator = msg.denominator
                    break
                    
        # Calculate ticks per measure
        ticks_per_measure = ticks_per_beat * 4 * time_sig_numerator / time_sig_denominator
        
        # Convert MIDI ticks to seconds for each measure
        tempo = 500000  # Default tempo (microseconds per beat)
        for track in self.midi_file.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    tempo = msg.tempo
                    break
                    
        seconds_per_tick = tempo / (ticks_per_beat * 1000000)
        seconds_per_measure = ticks_per_measure * seconds_per_tick
        
        # Draw measure lines
        current_time = 0
        canvas_width = self.viz_canvas.winfo_width()
        
        while current_time <= max(time for time, _ in self.midi_messages):
            y_pos = current_time * self.pixels_per_second
            y_pos = self.max_height - y_pos  # Invert position
            
            # Draw measure line
            line_id = self.viz_canvas.create_line(
                0, y_pos,
                canvas_width, y_pos,
                fill="#303030",  # Dark gray color
                width=1,
                dash=(2, 4)  # Dashed line pattern
            )
            
            # Add measure number
            measure_num = int(current_time / seconds_per_measure) + 1
            self.viz_canvas.create_text(
                10, y_pos - 5,
                text=f"M{measure_num}",
                fill="#505050",  # Medium gray color
                anchor="sw",
                font=("TkDefaultFont", 8)
            )
            
            current_time += seconds_per_measure

    def get_note_x_position(self, midi_note):
        """Get x-position for a MIDI note with fixed positioning"""
        try:
            # Get canvas width
            viz_width = self.viz_canvas.winfo_width()
            if viz_width <= 0:
                print(f"Invalid canvas width: {viz_width}")
                return None
            
            # Calculate spacing - 88 notes on piano (21-108)
            note_spacing = viz_width / 88
            
            # Calculate x position based on note index (0-87)
            note_index = midi_note - 21  # Convert MIDI note (21-108) to index (0-87)
            if not (0 <= note_index < 88):
                print(f"Note index {note_index} out of range")
                return None
                
            # Center note rectangle in its space
            x_pos = note_index * note_spacing + (note_spacing - self.note_width) / 2
            
            return x_pos
            
        except Exception as e:
            print(f"Error calculating x position: {str(e)}")
            return None

    def clear_visualization(self):
        """Clear all visualized notes"""
        if hasattr(self, 'viz_canvas') and self.viz_canvas.winfo_exists():
            self.viz_canvas.delete("all")
            self.max_height = 0

    def get_note_color(self, velocity):
        """Get color based on velocity"""
        return f"#{int(velocity * 2):02x}00{int(255 - velocity * 2):02x}"

    def on_viz_canvas_resize(self, event):
        """Handle visualization canvas resize events"""
        # Only handle if we have loaded MIDI messages
        if hasattr(self, 'midi_messages') and self.midi_messages:
            # Store current scroll position
            current_scroll = self.viz_canvas.yview()
            
            # Calculate fixed width based on new canvas size
            viz_width = event.width
            note_spacing = viz_width / 88  # Divide available width by number of notes
            self.note_width = min(15, note_spacing * 0.8)  # Adjust note width to fit spacing
            
            # Redraw all notes
            self.visualize_midi_file()
            
            # Restore scroll position
            self.viz_canvas.yview_moveto(current_scroll[0])

    def toggle_playback(self):
        """Toggle between play and pause states"""
        if not hasattr(self, 'midi_messages') or not self.midi_messages:
            return
            
        if not self.is_playing:
            self.start_playback()
        else:
            self.pause_playback()
    
    def start_playback(self):
        """Start or resume MIDI playback"""
        if not self.midi_output:
            return
            
        self.is_playing = True
        self.play_button.config(text="Pause")
        
        # If starting from beginning, reset playback index
        if self.playback_index >= len(self.midi_messages):
            self.playback_index = 0
            self.last_message_time = 0
        
        self.process_next_message()
    
    def pause_playback(self):
        """Pause MIDI playback"""
        self.is_playing = False
        self.play_button.config(text="Play")
        # Send all notes off to prevent hanging notes
        self.send_all_notes_off()
    
    def stop_playback(self):
        """Stop MIDI playback and reset to beginning"""
        self.is_playing = False
        self.play_button.config(text="Play")
        self.playback_index = 0
        self.last_message_time = 0
        # Send all notes off to prevent hanging notes
        self.send_all_notes_off()
        # Reset visualization scroll to top
        self.viz_canvas.yview_moveto(0.0)
    
    def process_next_message(self):
        """Process the next MIDI message in the sequence"""
        if not self.is_playing or self.playback_index >= len(self.midi_messages):
            if self.playback_index >= len(self.midi_messages):
                self.stop_playback()  # Auto-stop at end
            return
            
        current_time, msg = self.midi_messages[self.playback_index]
        
        # Calculate delay until next message
        if self.playback_index == 0:
            delay = 0
        else:
            delay = (current_time - self.last_message_time) * 1000  # Convert to milliseconds
        
        # Send message after delay
        def send_delayed_message():
            if not self.is_playing:
                return
                
            if msg.type in ['note_on', 'note_off']:
                # Apply velocity scaling for note_on messages
                if msg.type == 'note_on':
                    velocity = int((msg.velocity * self.velocity_value.get()) / 100)
                    msg_to_send = mido.Message('note_on', note=msg.note, velocity=velocity)
                else:
                    msg_to_send = msg
                    
                self.midi_output.send(msg_to_send)
                
                # Highlight active key
                self.highlight_playing_key(msg.note, msg.type == 'note_on' and msg.velocity > 0)
                
                # Update visualization scroll position
                self.update_visualization_scroll(current_time)
            
            self.last_message_time = current_time
            self.playback_index += 1
            self.process_next_message()
        
        self.after(int(delay), send_delayed_message)
    
    def highlight_playing_key(self, note, is_on):
        """Highlight or unhighlight a key during playback"""
        # Find the key_id for this note
        key_id = None
        for k, n in self.active_keys.items():
            if n == note:
                key_id = k
                break
        
        if key_id:
            if is_on:
                self.canvas.itemconfig(key_id, fill="blue")
            else:
                original_color = self.key_colors[key_id]
                self.canvas.itemconfig(key_id, fill=original_color)
    
    def update_visualization_scroll(self, current_time):
        """Update visualization scroll position during playback"""
        if not hasattr(self, 'viz_canvas'):
            return
            
        # Calculate the position in the visualization
        y_position = current_time * self.pixels_per_second
        total_height = self.viz_canvas.winfo_height()
        scroll_region = self.viz_canvas.bbox('all')
        
        if not scroll_region:
            return
            
        # Calculate the fraction to scroll (inverted since visualization is bottom-up)
        _, _, _, scroll_height = scroll_region
        if scroll_height <= total_height:
            return
            
        # Keep the playback position in the middle of the visible area
        middle_offset = total_height / 2
        target_y = y_position - middle_offset
        
        # Convert to scroll fraction (0 to 1)
        scroll_fraction = max(0, min(1, target_y / (scroll_height - total_height)))
        
        # Apply scroll
        self.viz_canvas.yview_moveto(1 - scroll_fraction)

    def refresh_midi_ports(self):
        """Refresh the list of available MIDI ports in the dropdowns"""
        # Update input ports
        input_ports = ["None"] + mido.get_input_names()
        self.midi_input_dropdown['values'] = input_ports
        
        # Update output ports
        output_ports = ["None"] + mido.get_output_names()
        self.midi_output_dropdown['values'] = output_ports
        
        # Maintain current selections if they still exist in the port lists
        if self.midi_input_var.get() not in input_ports:
            self.midi_input_var.set("None")
        if self.midi_output_var.get() not in output_ports:
            self.midi_output_var.set("None")
            
    def start_midi_callback(self):
        """Start the MIDI input callback loop"""
        if self.midi_input:
            try:
                for msg in self.midi_input.iter_pending():
                    self.on_midi_input(msg)
            except Exception as e:
                print(f"Error reading MIDI input: {e}")
        
        # Schedule next callback
        self.after(1, self.start_midi_callback)

    def periodic_port_refresh(self):
        """Periodically refresh MIDI ports to detect changes"""
        self.refresh_midi_ports()
        self.after(5000, self.periodic_port_refresh)  # Check every 5 seconds

if __name__ == "__main__":
    app = SynthesiaKeyboard()
    app.mainloop()
