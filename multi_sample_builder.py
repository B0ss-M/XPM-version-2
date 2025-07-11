import os
import glob
import logging
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from xpm_parameter_editor import name_to_midi, extract_root_note_from_wav

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def midi_to_name(num: int) -> str:
    """Convert a MIDI note number to a name like ``C4``."""
    return NOTE_NAMES[num % 12] + str(num // 12 - 1)

AUDIO_EXTS = ('.wav', '.aif', '.aiff', '.flac', '.mp3', '.ogg', '.m4a')


def parse_filename_mapping(filename):
    """Return a group name and mapping info parsed from ``filename``.

    The function looks for patterns like ``Name_A2-B2_1-64.wav`` where
    ``A2-B2`` defines the note range and ``1-64`` defines the velocity
    range. It returns a tuple ``(group_name, mapping_dict or None)``.
    """
    base = os.path.splitext(os.path.basename(filename))[0]
    m = re.search(r"^(.*?)[ _-]([A-G][#b]?\d+(?:-[A-G][#b]?\d+)?)[ _-](\d+)-(\d+)$", base, re.IGNORECASE)
    if m:
        name, note_range, v_low, v_high = m.groups()
        notes = note_range.split("-")
        low = name_to_midi(notes[0])
        high = name_to_midi(notes[-1])
        if low is not None and high is not None:
            mapping = {
                "root_note": low,
                "low_note": low,
                "high_note": high,
                "velocity_low": int(v_low),
                "velocity_high": int(v_high),
            }
            return name.strip(), mapping

    m = re.search(r"^(.*?)[ _-]([A-G][#b]?\d+(?:-[A-G][#b]?\d+)?)$", base, re.IGNORECASE)
    if m:
        name, note_range = m.groups()
        notes = note_range.split("-")
        low = name_to_midi(notes[0])
        high = name_to_midi(notes[-1])
        if low is not None and high is not None:
            mapping = {
                "root_note": low,
                "low_note": low,
                "high_note": high,
            }
            return name.strip(), mapping

    return os.path.splitext(os.path.basename(filename))[0], None

class MultiSampleBuilderWindow(tk.Toplevel):
    """Interactive tool for grouping samples and creating multi-sample instruments."""

    def __init__(self, master, builder_cls, options_cls, default_mode="multi-sample"):
        super().__init__(master.root)
        self.master = master
        self.builder_cls = builder_cls
        self.options_cls = options_cls
        self.default_mode = default_mode
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

        btn_ag_prefix = ttk.Button(left_btns, text="Auto Group Prefix", command=self.auto_group)
        btn_ag_folders = ttk.Button(left_btns, text="Auto Group Folders", command=self.auto_group_folders)
        btn_group_sel = ttk.Button(left_btns, text="Group Selected", command=self.group_selected_prefix)
        btn_detect_note = ttk.Button(left_btns, text="Detect Root Note", command=self.detect_root_note)
        btn_add_group = ttk.Button(left_btns, text="Add to Group →", command=self.add_selected)

        btn_ag_prefix.grid(row=0, column=0, sticky="w")
        btn_ag_folders.grid(row=0, column=1, padx=(5, 0), sticky="w")
        btn_group_sel.grid(row=0, column=2, padx=(5, 0), sticky="w")
        btn_detect_note.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))
        btn_add_group.grid(row=1, column=2, sticky="e", pady=(5, 0))

        for i in range(3):
            left_btns.grid_columnconfigure(i, weight=1)

        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True, padx=(10,0))
        top = ttk.Frame(right)
        top.pack(fill="x")
        ttk.Label(top, text="Groups:").pack(side="left")
        self.group_combo = ttk.Combobox(top, textvariable=self.group_var, state="readonly")
        self.group_combo.pack(side="left", fill="x", expand=True)
        self.group_combo.bind("<<ComboboxSelected>>", self.refresh_group_files)
        ttk.Button(top, text="Add Group", command=self.add_group).pack(side="left", padx=5)
        ttk.Button(top, text="Rename Group", command=self.rename_group).pack(side="left")
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
        ttk.Combobox(bottom, textvariable=self.map_var, state="readonly", values=["all", "white", "black"]).pack(side="left")
        ttk.Button(bottom, text="Build Instruments", command=self.build).pack(side="right")

    def load_files(self):
        folder = self.master.folder_path.get()
        if hasattr(self, 'folder_label'):
            self.folder_label.config(text=folder)
        pattern = os.path.join(folder, '**', '*') if self.master.recursive_scan_var.get() else os.path.join(folder, '*')
        all_files = glob.glob(pattern, recursive=self.master.recursive_scan_var.get())
        files = [f for f in all_files if os.path.splitext(f)[1].lower() in AUDIO_EXTS]
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

    def rename_group(self):
        grp = self.group_var.get()
        if grp not in self.groups:
            return
        new_name = simpledialog.askstring("Rename Group", "Enter new name:", parent=self, initialvalue=grp)
        if new_name and new_name not in self.groups:
            self.groups[new_name] = self.groups.pop(grp)
            self.group_var.set(new_name)
            self.refresh_group_combo()

    def add_selected(self):
        grp = self.group_var.get()
        if grp not in self.groups:
            messagebox.showwarning("No Group", "Please select or create a group first.", parent=self)
            return
        selections = [self.file_list.get(i) for i in self.file_list.curselection()]
        for fname in selections:
            if fname in self.unassigned:
                self.unassigned.remove(fname)
                self.groups[grp].append(fname)
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
            group_name, _ = parse_filename_mapping(f)
            if not group_name:
                group_name = os.path.basename(f)[:5].upper()
            self.groups.setdefault(group_name, []).append(f)
            self.unassigned.remove(f)
        self.refresh_file_list()

    def group_selected_prefix(self):
        """Create a new group from the selected files using the prefix before ``_``."""
        selections = [self.file_list.get(i) for i in self.file_list.curselection()]
        if not selections:
            return
        prefix = os.path.basename(selections[0]).split('_')[0]
        name = prefix or 'Group'
        counter = 1
        base_name = name
        while name in self.groups:
            counter += 1
            name = f"{base_name}_{counter}"
        self.groups[name] = []
        self.group_var.set(name)
        for fname in selections:
            if fname in self.unassigned:
                self.unassigned.remove(fname)
                self.groups[name].append(fname)
        self.refresh_file_list()
        self.refresh_group_files()

    def auto_group_folders(self):
        """Preview and group unassigned samples by common filename prefixes."""
        counts = {}
        for f in self.unassigned:
            name, _ = parse_filename_mapping(f)
            if not name:
                base = os.path.splitext(os.path.basename(f))[0]
                name = re.split(r"[ _-]+", base)[0]
            counts[name] = counts.get(name, 0) + 1

        preview = tk.Toplevel(self)
        preview.title("Auto Group Folders")
        preview.geometry("300x300")

        tree = ttk.Treeview(preview, columns=("count"), show="headings")
        tree.heading("#1", text="Group")
        tree.heading("count", text="Files")
        for folder, cnt in sorted(counts.items()):
            tree.insert("", "end", values=(folder, cnt))
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        btns = ttk.Frame(preview)
        btns.pack(fill="x", padx=10, pady=5)

        def do_group():
            for f in list(self.unassigned):
                name, _ = parse_filename_mapping(f)
                if not name:
                    base = os.path.splitext(os.path.basename(f))[0]
                    name = re.split(r"[ _-]+", base)[0]
                self.groups.setdefault(name, []).append(f)
                self.unassigned.remove(f)
            self.refresh_file_list()
            preview.destroy()

        ttk.Button(btns, text="Group", command=do_group).pack(side="right")
        ttk.Button(btns, text="Cancel", command=preview.destroy).pack(side="right", padx=(0,5))

    def detect_root_note(self):
        """Analyze selected files and append detected root note to their names."""
        selections = [self.file_list.get(i) for i in self.file_list.curselection()]
        if not selections:
            return
        folder = self.master.folder_path.get()
        for rel in selections:
            path = os.path.join(folder, rel)
            note = extract_root_note_from_wav(path)
            if note is None:
                continue
            base, ext = os.path.splitext(os.path.basename(path))
            if re.search(r'_[A-G][#b]?\d+$', base, re.IGNORECASE):
                continue
            note_name = midi_to_name(note)
            new_base = f"{base}_{note_name}"
            new_path = os.path.join(os.path.dirname(path), new_base + ext)
            try:
                os.rename(path, new_path)
            except Exception as exc:
                logging.error("Rename failed for %s: %s", path, exc)
                continue
            new_rel = os.path.relpath(new_path, folder)
            idx = self.unassigned.index(rel)
            self.unassigned[idx] = new_rel
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

        popup = tk.Toplevel(self)
        popup.title("Select Build Mode")

        mode_var = tk.StringVar(value=self.default_mode)
        ttk.Radiobutton(
            popup,
            text="Instrument Keygroup",
            variable=mode_var,
            value="multi-sample",
        ).pack(anchor="w", padx=10, pady=5)
        ttk.Radiobutton(
            popup,
            text="One-Shot Keygroup",
            variable=mode_var,
            value="one-shot",
        ).pack(anchor="w", padx=10)
        ttk.Radiobutton(
            popup, text="Drum Program", variable=mode_var, value="drum-kit"
        ).pack(anchor="w", padx=10)

        format_frame = ttk.Frame(popup)
        format_frame.pack(fill="x", padx=10)
        ttk.Label(format_frame, text="Format:").pack(side="left")
        default_format = 'advanced'
        if hasattr(self.master, 'format_var'):
            val = self.master.format_var
            default_format = val.get() if hasattr(val, 'get') else str(val)
        format_var = tk.StringVar(value=default_format)
        ttk.Combobox(
            format_frame,
            textvariable=format_var,
            values=["legacy", "advanced"],
            state="readonly",
            width=10,
        ).pack(side="left", padx=(5, 0))

        btn_frame = ttk.Frame(popup)
        btn_frame.pack(fill="x", padx=10, pady=5)

        def start_build():
            popup.destroy()
            logging.info("MultiSampleBuilderWindow.build starting")
            options = self.options_cls(
                loop_one_shots=self.master.loop_one_shots_var.get(),
                analyze_scw=self.master.analyze_scw_var.get(),
                creative_mode=self.master.creative_mode_var.get(),
                recursive_scan=False,
                firmware_version=self.master.firmware_version.get(),
                polyphony=self.master.polyphony_var.get(),
                format_version=format_var.get(),
                creative_config=self.master.creative_config,
            )
            builder = self.builder_cls(self.master.folder_path.get(), self.master, options)
            map_mode = self.map_var.get()
            for name, files in self.groups.items():
                logging.info("Building group '%s' with %d file(s)", name, len(files))
                mappings = []
                for f in files:
                    _, mapping = parse_filename_mapping(f)
                    if mapping is None:
                        mappings = None
                        break
                    mapping['sample_path'] = os.path.join(self.master.folder_path.get(), f)
                    mappings.append(mapping)
                output_folder = os.path.dirname(
                    os.path.join(self.master.folder_path.get(), files[0])
                )
                if mappings:
                    builder._create_xpm(
                        name,
                        files,
                        output_folder,
                        mode_var.get(),
                        mappings=mappings,
                    )
                else:
                    notes = None
                    if mode_var.get() != "one-shot":
                        notes = self.generate_notes(len(files), map_mode)
                    builder._create_xpm(
                        name,
                        files,
                        output_folder,
                        mode_var.get(),
                        midi_notes=notes,
                    )
            messagebox.showinfo("Done", "Instruments created.", parent=self)
            self.destroy()

        ttk.Button(btn_frame, text="Build", command=start_build).pack(side="right")
        ttk.Button(btn_frame, text="Cancel", command=popup.destroy).pack(side="right", padx=(0,5))
