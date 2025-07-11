import tkinter as tk
from tkinter import ttk, messagebox
import os
import glob
import re
import threading
from collections import defaultdict

# Define common audio extensions
AUDIO_EXTS = ['.wav']

class MultiSampleBuilderWindow(tk.Toplevel):
    """
    A GUI window for interactively building multi-sampled, one-shot, or drum kit
    XPM programs by selecting and grouping audio files.
    """
    def __init__(self, master, builder_class, options_class, mode='multi-sample'):
        """
        Initializes the MultiSampleBuilderWindow.

        Args:
            master: The parent window (main App instance).
            builder_class: The InstrumentBuilder class from the main script.
            options_class: The InstrumentOptions dataclass from the main script.
            mode (str): The build mode ('multi-sample', 'one-shot', 'drum-kit').
        """
        super().__init__(master)
        self.master = master
        self.builder_class = builder_class
        self.options_class = options_class
        self.mode = mode
        self.folder_path = self.master.folder_path.get()

        self.title(f"Build {mode.replace('-', ' ').title()} Programs")
        self.geometry("800x600")
        self.resizable(True, True)

        self.create_widgets()
        self.scan_files()

    def create_widgets(self):
        """Creates and lays out the widgets for the window."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Top frame for controls
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ttk.Button(top_frame, text="Rescan Files", command=self.scan_files).pack(side="left")
        ttk.Button(top_frame, text="Group Selected", command=self.group_selected).pack(side="left", padx=10)
        ttk.Button(top_frame, text="Auto-Group by Prefix", command=self.auto_group_by_prefix).pack(side="left")

        # Treeview for displaying files
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame, columns=("File", "Program"), show="headings")
        self.tree.heading("File", text="Audio File")
        self.tree.heading("Program", text="Target Program Name")
        self.tree.column("File", width=400)
        self.tree.column("Program", width=300)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Bottom frame for action buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.create_button = ttk.Button(bottom_frame, text="Create Programs", command=self.create_programs, style="Accent.TButton", state="disabled")
        self.create_button.pack(side="right")
        ttk.Button(bottom_frame, text="Close", command=self.destroy).pack(side="right", padx=5)

    def scan_files(self):
        """Scans the selected folder for audio files and populates the treeview."""
        for i in self.tree.get_children():
            self.tree.delete(i)

        if not self.folder_path or not os.path.isdir(self.folder_path):
            messagebox.showwarning("No Folder", "Please select a source folder first.", parent=self)
            return

        # Use recursive scan option from the main app
        recursive = self.master.recursive_scan_var.get()
        search_path = os.path.join(self.folder_path, '**') if recursive else self.folder_path

        all_files = []
        for ext in AUDIO_EXTS:
            all_files.extend(glob.glob(os.path.join(search_path, f'*{ext}'), recursive=recursive))

        for file_path in sorted(all_files):
            rel_path = os.path.relpath(file_path, self.folder_path)
            # Default program name is the file's basename without extension
            default_program = os.path.splitext(os.path.basename(rel_path))[0]
            self.tree.insert('', 'end', values=(rel_path, default_program))

        if self.tree.get_children():
            self.create_button.config(state="normal")

    def group_selected(self):
        """Groups all selected files under the program name of the first selected item."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select two or more files to group.", parent=self)
            return

        # Use the program name of the first selected item as the group name
        first_item_values = self.tree.item(selected_items[0], 'values')
        group_name = first_item_values[1]

        for item in selected_items:
            current_values = list(self.tree.item(item, 'values'))
            current_values[1] = group_name
            self.tree.item(item, values=tuple(current_values))

    def auto_group_by_prefix(self):
        """Automatically groups files based on a shared prefix (e.g., 'Piano_')."""
        groups = defaultdict(list)
        for item in self.tree.get_children():
            filename = self.tree.item(item, 'values')[0]
            # Find a prefix ending with a common separator
            match = re.match(r'(.+?)[_ -]', filename)
            if match:
                prefix = match.group(1)
                groups[prefix].append(item)

        for group_name, items in groups.items():
            if len(items) > 1:
                for item in items:
                    current_values = list(self.tree.item(item, 'values'))
                    current_values[1] = group_name
                    self.tree.item(item, values=tuple(current_values))

    def create_programs(self):
        """
        Gathers user selections from the UI and delegates the build process
        to the main InstrumentBuilder class.
        """
        programs_to_build = defaultdict(list)
        for item in self.tree.get_children():
            file_path, program_name = self.tree.item(item, 'values')
            if program_name:
                programs_to_build[program_name].append(file_path)

        if not programs_to_build:
            messagebox.showerror("Error", "No programs are defined. Please assign files to programs.", parent=self)
            return

        self.destroy() # Close the builder window before starting the process

        # Get the latest options from the main app
        options = self.options_class(
            loop_one_shots=self.master.loop_one_shots_var.get(),
            analyze_scw=self.master.analyze_scw_var.get(),
            creative_mode=self.master.creative_mode_var.get(),
            recursive_scan=self.master.recursive_scan_var.get(),
            firmware_version=self.master.firmware_version.get(),
            polyphony=self.master.polyphony_var.get(),
            creative_config=self.master.creative_config
        )

        # Instantiate the main builder class
        builder = self.builder_class(self.folder_path, self.master, options=options)

        # Run the creation process in a separate thread
        threading.Thread(
            target=builder.create_instruments,
            args=(self.mode,),
            kwargs={'files': programs_to_build}, # Pass the user-defined groups
            daemon=True
        ).start()

