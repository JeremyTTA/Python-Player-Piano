import mido
import os
import tkinter as tk
from tkinter import filedialog, ttk

# General MIDI instrument names (0-127)
GM_INSTRUMENTS = [
    "Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano", "Honky-tonk Piano",
    "Electric Piano 1", "Electric Piano 2", "Harpsichord", "Clavi", "Celesta", "Glockenspiel",
    "Music Box", "Vibraphone", "Marimba", "Xylophone", "Tubular Bells", "Dulcimer",
    "Drawbar Organ", "Percussive Organ", "Rock Organ", "Church Organ", "Reed Organ",
    "Accordion", "Harmonica", "Tango Accordion", "Acoustic Guitar (nylon)", "Acoustic Guitar (steel)",
    "Electric Guitar (jazz)", "Electric Guitar (clean)", "Electric Guitar (muted)", "Overdriven Guitar",
    "Distortion Guitar", "Guitar harmonics", "Acoustic Bass", "Electric Bass (finger)",
    "Electric Bass (pick)", "Fretless Bass", "Slap Bass 1", "Slap Bass 2", "Synth Bass 1",
    "Synth Bass 2", "Violin", "Viola", "Cello", "Contrabass", "Tremolo Strings", "Pizzicato Strings",
    "Orchestral Harp", "Timpani", "String Ensemble 1", "String Ensemble 2", "SynthStrings 1",
    "SynthStrings 2", "Choir Aahs", "Voice Oohs", "Synth Voice", "Orchestra Hit", "Trumpet",
    "Trombone", "Tuba", "Muted Trumpet", "French Horn", "Brass Section", "SynthBrass 1",
    "SynthBrass 2", "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax", "Oboe",
    "English Horn", "Bassoon", "Clarinet", "Piccolo", "Flute", "Recorder", "Pan Flute",
    "Blown Bottle", "Shakuhachi", "Whistle", "Ocarina", "Lead 1 (square)", "Lead 2 (sawtooth)",
    "Lead 3 (calliope)", "Lead 4 (chiff)", "Lead 5 (charang)", "Lead 6 (voice)", "Lead 7 (fifths)",
    "Lead 8 (bass + lead)", "Pad 1 (new age)", "Pad 2 (warm)", "Pad 3 (polysynth)", "Pad 4 (choir)",
    "Pad 5 (bowed)", "Pad 6 (metallic)", "Pad 7 (halo)", "Pad 8 (sweep)", "FX 1 (rain)",
    "FX 2 (soundtrack)", "FX 3 (crystal)", "FX 4 (atmosphere)", "FX 5 (brightness)",
    "FX 6 (goblins)", "FX 7 (echoes)", "FX 8 (sci-fi)", "Sitar", "Banjo", "Shamisen",
    "Koto", "Kalimba", "Bag pipe", "Fiddle", "Shanai", "Tinkle Bell", "Agogo", "Steel Drums",
    "Woodblock", "Taiko Drum", "Melodic Tom", "Synth Drum", "Reverse Cymbal", "Guitar Fret Noise",
    "Breath Noise", "Seashore", "Bird Tweet", "Telephone Ring", "Helicopter", "Applause",
    "Gunshot"
]

class MidiChannelEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("MIDI Channel Editor")
        self.root.geometry("500x450")
        
        self.midi_file = None
        self.file_path = None
        self.channel_vars = []  # List to hold checkbutton variables
        
        self.setup_gui()
        
    def setup_gui(self):
        """Set up the graphical interface with checkboxes."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Button(main_frame, text="Select MIDI File", command=self.load_midi_file).grid(row=0, column=0, pady=5, sticky=tk.W)
        self.file_label = ttk.Label(main_frame, text="No MIDI file selected")
        self.file_label.grid(row=1, column=0, pady=5, sticky=tk.W)
        
        # Canvas with scrollbar for channels
        self.canvas = tk.Canvas(main_frame, height=250)
        self.canvas.grid(row=2, column=0, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))
        self.canvas.config(yscrollcommand=scrollbar.set)
        
        # Frame inside canvas for checkboxes
        self.channel_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.channel_frame, anchor="nw")
        
        ttk.Button(main_frame, text="Delete Selected Channels", command=self.delete_channel).grid(row=3, column=0, pady=5, sticky=tk.W)
        ttk.Button(main_frame, text="Save Edited File", command=self.save_midi_file).grid(row=4, column=0, pady=5, sticky=tk.W)
        
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.grid(row=5, column=0, pady=5, sticky=tk.W)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
    def load_midi_file(self):
        """Load a MIDI file and list channels with checkboxes."""
        file_path = filedialog.askopenfilename(
            title="Select MIDI File",
            filetypes=[("MIDI files", "*.mid *.midi")]
        )
        
        if file_path:
            try:
                self.midi_file = mido.MidiFile(file_path)
                self.file_path = file_path
                self.file_label.config(text=f"Selected: {os.path.basename(file_path)}")
                self.update_channel_list()
                self.status_label.config(text="File loaded successfully")
            except Exception as e:
                self.status_label.config(text=f"Error: Failed to load file - {e}")
                self.midi_file = None
                self.file_path = None
                self.file_label.config(text="No MIDI file selected")
                self.clear_channel_list()
        
    def get_channel_info(self):
        """Extract channel numbers and their associated names."""
        if not self.midi_file:
            return {}
        
        channel_info = {i: f"Channel {i}" for i in range(16)}  # Default names
        
        for track_idx, track in enumerate(self.midi_file.tracks):
            track_name = None
            channel_programs = {}
            
            for msg in track:
                if msg.type == 'track_name':
                    track_name = msg.name
                elif msg.type == 'program_change':
                    channel = msg.channel
                    program = msg.program
                    if 0 <= program < len(GM_INSTRUMENTS):
                        channel_programs[channel] = GM_INSTRUMENTS[program]
                elif hasattr(msg, 'channel'):
                    channel = msg.channel
                    if channel not in channel_programs and track_name:
                        channel_programs[channel] = track_name
            
            for channel, name in channel_programs.items():
                channel_info[channel] = f"Ch {channel}: {name}"
        
        used_channels = {}
        for track in self.midi_file.tracks:
            for msg in track:
                if hasattr(msg, 'channel'):
                    channel = msg.channel
                    if channel in channel_info:
                        used_channels[channel] = channel_info[channel]
        
        return used_channels
        
    def update_channel_list(self):
        """Populate the channel frame with checkboxes."""
        self.clear_channel_list()
        channel_info = self.get_channel_info()
        self.channel_vars = []
        
        for i, (channel, name) in enumerate(sorted(channel_info.items())):
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(self.channel_frame, text=name, variable=var)
            cb.grid(row=i, column=0, sticky=tk.W, pady=2)
            self.channel_vars.append((channel, name, var))
        
        # Update canvas scroll region
        self.channel_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
    def clear_channel_list(self):
        """Clear all checkboxes from the channel frame."""
        for widget in self.channel_frame.winfo_children():
            widget.destroy()
        self.channel_vars = []
        
    def delete_channel(self):
        """Remove all messages for the selected channels."""
        if not self.midi_file:
            self.status_label.config(text="Error: No MIDI file loaded")
            return
        
        channels_to_delete = []
        deleted_names = []
        for channel, name, var in self.channel_vars:
            if var.get():  # If checkbox is checked
                channels_to_delete.append(channel)
                deleted_names.append(name)
        
        if not channels_to_delete:
            self.status_label.config(text="Error: No channels selected")
            return
        
        for track in self.midi_file.tracks:
            new_messages = [msg for msg in track if not (hasattr(msg, 'channel') and msg.channel in channels_to_delete)]
            track[:] = new_messages
        
        self.update_channel_list()
        self.status_label.config(text=f"Deleted: {', '.join(deleted_names)}")
        
    def save_midi_file(self):
        """Save the edited MIDI file."""
        if not self.midi_file:
            self.status_label.config(text="Error: No MIDI file loaded")
            return
        
        base_name = os.path.splitext(self.file_path)[0]
        save_path = filedialog.asksaveasfilename(
            initialfile=f"{os.path.basename(base_name)}_edited.mid",
            defaultextension=".mid",
            filetypes=[("MIDI files", "*.mid")]
        )
        
        if save_path:
            try:
                self.midi_file.save(save_path)
                self.status_label.config(text=f"Saved as: {os.path.basename(save_path)}")
            except Exception as e:
                self.status_label.config(text=f"Error: Failed to save file - {e}")

def main():
    try:
        import mido
    except ImportError:
        tk.Tk().withdraw()
        from tkinter import messagebox
        messagebox.showerror("Error", "Please install mido:\nRun 'pip install mido' in your terminal.")
        return
    
    root = tk.Tk()
    app = MidiChannelEditor(root)
    root.mainloop()

if __name__ == "__main__":
    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    main()