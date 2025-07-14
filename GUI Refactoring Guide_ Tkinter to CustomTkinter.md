# **GUI Refactoring Guide: Migrating to CustomTkinter**

**Objective:** To update the Gemini wav\_TO\_XpmV2.py application interface from the standard tkinter.ttk library to the modern customtkinter library, matching the aesthetic of the provided reference images.

## **1\. Prerequisites**

First, ensure the customtkinter library is installed in the development environment.  
pip install customtkinter

## **2\. Initial Application Setup**

The initial changes involve modifying the main App class to use customtkinter as its base.  
**File to Modify:** Gemini wav\_TO\_XpmV2.py

### **2.1. Update Imports**

Replace the tkinter imports with customtkinter.  
**Current Code:**  
import tkinter as tk  
from tkinter import ttk, filedialog, messagebox

**New Code:**  
import customtkinter  
from tkinter import filedialog, messagebox \# Keep these for standard dialogs

*(Note: Standard dialogs like filedialog are not replaced by customtkinter and should be kept.)*

### **2.2. Update App Class Inheritance**

Change the App class to inherit from customtkinter.CTk.  
**Current Code:**  
class App(tk.Tk):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_()  
        \# ...  
        self.setup\_retro\_theme()

**New Code:**  
class App(customtkinter.CTk):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_()  
        \# ...  
        customtkinter.set\_appearance\_mode("Dark")  
        customtkinter.set\_default\_color\_theme("blue")  
        \# The setup\_retro\_theme() function and its call should be removed.

## **3\. Widget Refactoring Strategy**

The core of the work is to systematically replace ttk widgets with their customtkinter counterparts (CTk). This must be done for all GUI creation methods (e.g., create\_browser\_bar, create\_action\_buttons, create\_log\_viewer, etc.).  
The general mapping is as follows:

* ttk.Frame or ttk.LabelFrame \-\> customtkinter.CTkFrame  
* ttk.Button \-\> customtkinter.CTkButton  
* ttk.Label \-\> customtkinter.CTkLabel  
* ttk.Entry \-\> customtkinter.CTkEntry  
* ttk.Combobox \-\> customtkinter.CTkComboBox  
* ttk.Checkbutton \-\> customtkinter.CTkCheckBox  
* ttk.Progressbar \-\> customtkinter.CTkProgressBar  
* ttk.Scrollbar \-\> customtkinter.CTkScrollbar

### **Example: Refactoring create\_action\_buttons**

This example demonstrates how to refactor a section to match the visual style of the reference images.  
**Current ttk Code:**  
def create\_action\_buttons(self, parent):  
    frame \= ttk.LabelFrame(parent, text="Build Instruments", padding="10")  
    frame.grid(row=2, column=0, sticky='ew', pady=5)  
    \# ... more ttk code ...

**New customtkinter Code:**  
def create\_action\_buttons(self, parent):  
    \# Use CTkFrame for a modern container with a specific color  
    frame \= customtkinter.CTkFrame(parent, fg\_color="\#2E2E2E", corner\_radius=8)  
    frame.grid(row=2, column=0, sticky='ew', pady=(10, 5), padx=10)  
    frame.grid\_columnconfigure((0, 1), weight=1)

    \# Add a title label inside the frame  
    title\_label \= customtkinter.CTkLabel(frame, text="Build Instruments", font=("Segoe UI", 14, "bold"))  
    title\_label.grid(row=0, column=0, columnspan=2, pady=(5, 10), sticky="w", padx=10)

    \# Main build button with blue accent  
    build\_multi\_btn \= customtkinter.CTkButton(  
        frame,  
        text="Build Multi-Sampled Instruments",  
        font=("Segoe UI", 12, "bold")  
    )  
    build\_multi\_btn.grid(row=1, column=0, sticky="ew", padx=(10,5), pady=5)

    \# Secondary button  
    build\_one\_shot\_btn \= customtkinter.CTkButton(  
        frame,  
        text="Build One-Shot Instruments",  
        font=("Segoe UI", 12, "bold")  
    )  
    build\_one\_shot\_btn.grid(row=1, column=1, sticky="ew", padx=(5,10), pady=5)  
      
    \# Drum Kit button with red accent  
    build\_drum\_kit\_btn \= customtkinter.CTkButton(  
        frame,  
        text="Build Drum Kit",  
        font=("Segoe UI", 12, "bold"),  
        fg\_color="\#B91C1C",  
        hover\_color="\#A01818"  
    )  
    build\_drum\_kit\_btn.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 10))

## **4\. Handling the ttk.Treeview**

**This is a critical step.** customtkinter does **not** have a native Treeview widget. You must continue to use ttk.Treeview for the log viewer and any file lists, but it needs to be styled manually to match the dark theme.

### **Styling the ttk.Treeview**

A ttk.Style object must be used to configure the Treeview colors.  
def create\_log\_viewer(self, parent):  
    \# ... CTkFrame setup ...

    \# Style the standard Treeview to match the CustomTkinter theme  
    style \= ttk.Style()  
    style.theme\_use("default") \# Important: start from a basic theme  
      
    \# Configure Treeview colors  
    style.configure("Treeview",  
                    background="\#2E2E2E",  
                    foreground="\#DCE4EE",  
                    fieldbackground="\#2E2E2E",  
                    borderwidth=0)  
    style.map('Treeview', background=\[('selected', '\#007ACC')\]) \# Blue selection

    \# Configure Heading colors  
    style.configure("Treeview.Heading",  
                    background="\#414042",  
                    foreground="\#DCE4EE",  
                    font=("Segoe UI", 12, "bold"))  
    style.map("Treeview.Heading", background=\[('active', '\#5A5A5A')\])

    \# Create the Treeview instance  
    self.log\_treeview \= ttk.Treeview(log\_frame, style="Treeview")  
    \# ... setup columns and headings ...  
    self.log\_treeview.grid(...)

    \# Use a CTkScrollbar for consistency  
    scrollbar \= customtkinter.CTkScrollbar(log\_frame, command=self.log\_treeview.yview)  
    scrollbar.grid(...)  
    self.log\_treeview.configure(yscrollcommand=scrollbar.set)

## **5\. Refactoring Toplevel Windows**

The same refactoring process must be applied to all Toplevel windows defined in the script (e.g., ExpansionDoctorWindow, FileRenamerWindow, BatchProgramEditorWindow, etc.). Each of these classes should be updated to inherit from customtkinter.CTkToplevel and their internal widgets must be replaced.  
**Example:**  
\# Before  
class ExpansionDoctorWindow(tk.Toplevel):  
    \# ...

\# After  
class ExpansionDoctorWindow(customtkinter.CTkToplevel):  
    \# ...

By following these steps, the entire application GUI can be migrated to customtkinter, achieving the modern, professional appearance shown in the reference images.
