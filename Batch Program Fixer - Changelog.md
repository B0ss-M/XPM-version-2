# **Feature Update: The Batch Program Fixer**

This document outlines the recent overhaul of the Program Fixer utility within the Wav to XPM Converter script. The previous version worked on a single file at a time. This update transforms it into a powerful **batch-processing tool**, allowing you to analyze, repair, and modernize your entire .xpm program library with much greater efficiency.

> **Note:** This repository is linked with the Gemini assistant. All conversations and code changes are logged in `Codex Communication Log.md` and `Gemini_Codex_Log.ipynb`.
## **1\. Why Was This Feature Upgraded?**

While the original Program Fixer was useful, it was inefficient for users with large libraries. The need to fix files one-by-one was tedious. The goal of this upgrade was to introduce a true batch workflow, addressing the following needs:

* **Efficiency:** Users need to fix dozens or hundreds of programs at once, not just one.  
* **Consolidated Relinking:** When samples are missing from multiple programs, the user should only have to point to the correct folder once.  
* **Bulk Modernization:** Users should be able to upgrade an entire collection of legacy programs to a new firmware version in a single operation.

The new **Batch Program Fixer** was designed to meet these needs, providing a robust and time-saving solution for library management.

## **2\. What Was Done: The New Implementation**

The ProgramFixerWindow was replaced with a new BatchProgramFixerWindow. This involved a complete redesign of the user interface and the underlying logic.

### **a. New "Batch Program Fixer" Button**

The button in the "Advanced Tools" section has been updated to reflect the new functionality.  
\# In the App class, inside the create\_advanced\_tools method:  
ttk.Button(frame, text="Batch Program Fixer...", command=lambda: self.open\_window(BatchProgramFixerWindow)).grid(row=1, column=0, columnspan=2, sticky="ew", padx=2, pady=2)

### **b. The BatchProgramFixerWindow Class & Workflow**

The new window provides a completely different, batch-oriented workflow:

1. **Folder Selection:** Instead of a single file, you now select a **folder** containing all the .xpm programs you want to work with.  
2. **Scanning:** The tool scans the folder (and its subfolders) and populates a list with all found .xpm files, showing their current version and status.  
3. **Multi-Selection:** You can select the programs you want to process using checkboxes. "Select All" and "Deselect All" buttons are provided for convenience.  
4. **Batch Actions:** You can now run "Analyze & Relink" or "Rebuild" on all selected programs in a single click.

### **c. Revised Core Logic**

The logic was re-engineered to handle batch operations efficiently.

#### **Stage 1: Analyze & Relink Samples (Batch Mode)**

* **Aggregate Analysis:** The tool first loops through **all selected programs** and compiles a single, unique list of every missing sample file.  
* **One-Time Prompt:** It then prompts you **only once** to locate the folder containing the missing samples.  
* **Intelligent Relinking:** The tool iterates through the programs again, copying the found samples from your selected folder to the correct location alongside each .xpm and fixing the paths within the XML. This is vastly more efficient than the old one-by-one method.

#### **Stage 2: Rebuild for New Firmware (Batch Mode)**

* **Looping Rebuild:** When you click "Rebuild Selected," the tool iterates through every program you've checked.  
* **Robust Parsing & Rebuilding:** For each program, it performs the same "Clean Slate Rebuild" as before—parsing the sample map and using the InstrumentBuilder to generate a brand new, clean .xpm file targeted to your selected firmware.  
* **Status Updates:** The status for each file is updated in the list in real-time, showing "Rebuilding...", "Rebuilt", or "Error".
* **Unmapped Sample Detection:** The fixer scans each program's folder for audio
  files not referenced in the XPM. Starting with this release, you are asked
  whether to include these extras when rebuilding instead of adding them
  automatically.

## **3\. Critical Bug Fix**

A critical bug that caused the error join() argument must be str, bytes, or os.PathLike object, not 'NoneType' has been fixed.

* **Cause:** The error occurred when the parsing function (\_parse\_any\_xpm) encountered an empty XML tag, such as \<SampleFile\>\</SampleFile\> or \<SampleFile/\>. The code would read the tag's content as None and then fail when trying to join None to a directory path.  
* **Solution:** The parsing logic has been made more robust. It now explicitly checks that the .text content of an XML element is not empty before attempting to use it in a path operation. This prevents the error and allows the batch process to safely skip corrupted or empty tags without crashing.