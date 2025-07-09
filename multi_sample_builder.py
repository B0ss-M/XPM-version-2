import os
import glob
import logging
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class MultiSampleBuilderWindow(tk.Toplevel):
    """Interactive tool for grouping samples and creating multi-sample instruments."""

    def __init__(self, master, builder_cls, options_cls):
        super().__init__(master.root)
        self.master = master
        self.builder_cls = builder_cls
        self.options_cls = options_cls
        self.title("Multi-Sample Instrument Builder")
        self.geometry("750x500")
        self.groups = {}
        self.unassigned = []
        self.group_var = tk.StringVar()
        self.map_var = tk.StringVar(value="all")
        self.create_widgets()
        self.load_files()

    def create_widgets(self):
        path_frame = ttk.Frame(self, padding=(10, 5))
        path_frame.pack(fill="x")
        ttk.Label(path_frame, text="Source Folder:").pack(side="left")
        self.folder_label = ttk.Label(path_frame, text=self.master.folder_path.get())
        self.folder_label.pack(side="left", fill="x", expand=True)
        ttk.Button(path_frame, text="Refresh", command=self.load_files).pack(side="right")

        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)
        ttk.Label(left, text="Unassigned Samples:").pack(anchor="w")
        left_list_frame = ttk.Frame(left)
        left_list_frame.pack(fill="both", expand=True)
        self.file_list = tk.Listbox(left_list_frame, selectmode="extended")
        vsb_left = ttk.Scrollbar(left_list_frame, orient="vertical", command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=vsb_left.set)
        self.file_list.pack(side="left", fill="both", expand=True)
        vsb_left.pack(side="right", fill="y")
        left_btns = ttk.Frame(left)
        left_btns.pack(fill="x", pady=5)
        ttk.Button(left_btns, text="Auto Group Prefix", command=self.auto_group).pack(side="left")
        ttk.Button(left_btns, text="Auto Group Folders", command=self.auto_group_folders).pack(side="left", padx=(5,0))
        ttk.Button(left_btns, text="Add to Group →", command=self.add_selected).pack(side="right")

        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True, padx=(10,0))
        top = ttk.Frame(right)
        top.pack(fill="x")
        ttk.Label(top, text="Groups:").pack(side="left")
        self.group_combo = ttk.Combobox(top, textvariable=self.group_var, state="readonly")
        self.group_combo.pack(side="left", fill="x", expand=True)
        self.group_combo.bind("<<ComboboxSelected>>", self.refresh_group_files)
        ttk.Button(top, text="Add Group", command=self.add_group).pack(side="left", padx=5)
        ttk.Button(top, text="Remove Group", command=self.remove_group).pack(side="left")

        ttk.Label(right, text="Files in Group:").pack(anchor="w", pady=(5,0))
        group_list_frame = ttk.Frame(right)
        group_list_frame.pack(fill="both", expand=True)
        self.group_list = tk.Listbox(group_list_frame, selectmode="extended")
        vsb_right = ttk.Scrollbar(group_list_frame, orient="vertical", command=self.group_list.yview)
        self.group_list.configure(yscrollcommand=vsb_right.set)
        self.group_list.pack(side="left", fill="both", expand=True)
        vsb_right.pack(side="right", fill="y")
        group_btns = ttk.Frame(right)
        group_btns.pack(fill="x", pady=5)
        ttk.Button(group_btns, text="← Remove", command=self.remove_selected).pack(side="left")

        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")
        ttk.Label(bottom, text="Key Mapping:").pack(side="left")
        ttk.Combobox(bottom, textvariable=self.map_var, state="readonly",
                    values=["all", "white", "black", "filename"]).pack(side="left")
        ttk.Button(bottom, text="Build Instruments", command=self.build).pack(side="right")

    def load_files(self):
        folder = self.master.folder_path.get()
        if hasattr(self, 'folder_label'):
            self.folder_label.config(text=folder)
        pattern = os.path.join(folder, '**', '*') if self.master.recursive_scan_var.get() else os.path.join(folder, '*')
        all_files = glob.glob(pattern, recursive=self.master.recursive_scan_var.get())
        files = [f for f in all_files if f.lower().endswith('.wav')]
        self.unassigned = [os.path.relpath(f, folder) for f in files if '.xpm.wav' not in f.lower()]
        self.refresh_file_list()

    def refresh_file_list(self):
        self.file_list.delete(0, tk.END)
        for f in sorted(self.unassigned):
            self.file_list.insert(tk.END, f)
        self.refresh_group_combo()

    def refresh_group_combo(self):
        self.group_combo['values'] = list(self.groups.keys())
        if self.group_var.get() not in self.groups and self.groups:
            self.group_var.set(next(iter(self.groups)))
        self.refresh_group_files()

    def refresh_group_files(self, event=None):
        self.group_list.delete(0, tk.END)
        grp = self.group_var.get()
        if grp in self.groups:
            for f in self.groups[grp]:
                self.group_list.insert(tk.END, f)

    def add_group(self):
        name = simpledialog.askstring("Group Name", "Enter group name:", parent=self)
        if name and name not in self.groups:
            self.groups[name] = []
            self.group_var.set(name)
            self.refresh_group_combo()

    def remove_group(self):
        grp = self.group_var.get()
        if grp in self.groups:
            self.unassigned.extend(self.groups.pop(grp))
            self.group_var.set('')
            self.refresh_file_list()

    def add_selected(self):
        grp = self.group_var.get()
        if grp not in self.groups:
            messagebox.showwarning("No Group", "Please select or create a group first.", parent=self)
            return
        indices = list(self.file_list.curselection())
        for i in reversed(indices):
            f = self.unassigned.pop(i)
            self.groups[grp].append(f)
        self.refresh_file_list()
        self.refresh_group_files()

    def remove_selected(self):
        grp = self.group_var.get()
        if grp not in self.groups:
            return
        indices = list(self.group_list.curselection())
        for i in reversed(indices):
            f = self.groups[grp].pop(i)
            self.unassigned.append(f)
        self.refresh_file_list()
        self.refresh_group_files()

    def auto_group(self):
        for f in list(self.unassigned):
            name = os.path.basename(f)[:5].upper()
            self.groups.setdefault(name, []).append(f)
            self.unassigned.remove(f)
        self.refresh_file_list()

    def auto_group_folders(self):
        """Group unassigned samples by their parent folder names."""
        for f in list(self.unassigned):
            folder = os.path.dirname(f)
            name = os.path.basename(folder) if folder else os.path.basename(self.master.folder_path.get())
            self.groups.setdefault(name, []).append(f)
            self.unassigned.remove(f)
        self.refresh_file_list()

    def generate_notes(self, count, mode):
        notes, note = [], 60
        while len(notes) < count and note < 128:
            if mode == 'white' and note % 12 in [1,3,6,8,10]:
                note += 1
                continue
            if mode == 'black' and note % 12 not in [1,3,6,8,10]:
                note += 1
                continue
            notes.append(note)
            note += 1
        return notes

    def build(self):
        if not self.groups:
            messagebox.showwarning("No Groups", "No groups defined.", parent=self)
            return
        logging.info("MultiSampleBuilderWindow.build starting")
        options = self.options_cls(
            loop_one_shots=self.master.loop_one_shots_var.get(),
            analyze_scw=self.master.analyze_scw_var.get(),
            creative_mode=self.master.creative_mode_var.get(),
            recursive_scan=False,
            firmware_version=self.master.firmware_version.get(),
            polyphony=self.master.polyphony_var.get(),
            voice_mode=self.master.voice_mode_var.get(),
            creative_config=self.master.creative_config
        )
        builder = self.builder_cls(self.master.folder_path.get(), self.master, options)
        mode = self.map_var.get()
        for name, files in self.groups.items():
            logging.info("Building group '%s' with %d file(s)", name, len(files))
            notes = None if mode == 'filename' else self.generate_notes(len(files), mode)
            builder._create_xpm(
                name,
                files,
                self.master.folder_path.get(),
                'multi-sample',
                midi_notes=notes,
            )
        messagebox.showinfo("Done", "Instruments created.", parent=self)
        self.destroy()
