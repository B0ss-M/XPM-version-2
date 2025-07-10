# Agent Collaboration Guide for `Gemini wav_TO_XpmV2.py`

\*\*Document Version:\*\* 1.1
\*\*Last Updated:\*\* July 4, 2025
\*\*Canonical Script Name:\*\* `Gemini wav_TO_XpmV2.py`

\#\# 1\. Project Objective

The primary goal of this project is to maintain a robust, feature-rich Python script. The stable GUI application is `Gemini wav_TO_XpmV2.py`, which supersedes the earlier `Wav_To_Xpm_Converter_v22.py` naming. This tool serves as a comprehensive toolkit for creating and managing Akai MPC Keygroup programs (`.xpm` files).

The script must be:  
\- \*\*User-Friendly\*\*: Operated via a clear Tkinter GUI.  
\- \*\*Powerful\*\*: Offering both basic one-shot/multi-sample conversion and advanced tools for layering, batch editing, and packaging.  
\- \*\*Compatible\*\*: Capable of both creating modern programs and correctly reading/processing legacy \`.xpm\` files from older MPC hardware and software.  
\- \*\*Stable\*\*: Free of errors, crashes, or incomplete features.

\#\# 2\. Current Project Status

As of this version, the project is considered \*\*stable and feature-complete\*\*. All core functions and advanced tools have been fully implemented and debugged. The application launches correctly, handles all known XPM versions, and all GUI buttons are wired to functional backend logic.

\*\*Any future work should be treated as an enhancement or a specific bug fix, not a foundational build.\*\*

\#\# 3\. CRITICAL DIRECTIVES FOR ALL AGENTS

Failure to adhere to these directives will likely break the application. \*\*These are not suggestions; they are rules.\*\*

\#\#\# Rule \#1: Do Not Break Existing Code  
This is the most important rule. The current script in the canvas document \`wav\_to\_xpm\_converter\_v22\` is the \*\*single source of truth\*\*. It works. Before implementing any change, you must understand the existing logic. \*\*Do not rewrite entire functions from scratch if an edit will suffice.\*\* Your primary goal is to preserve existing functionality while adding new capabilities or fixing specific, identified bugs.

\#\#\# Rule \#2: The Canvas is the Ground Truth  
Always refer to the most up-to-date version of the \`wav\_to\_xpm\_converter\_v22\` immersive document. Do not rely on code from the conversational history, as it may be outdated or contain previously fixed errors. Every edit must be a direct modification of the current, working canvas file.

\#\#\# Rule \#3: No Incomplete Code or Placeholders  
All features must be fully implemented. Do not create placeholder windows or functions that are not wired into the application. If a feature is added, it must be 100% functional upon delivery.

\#\#\# Rule \#4: Maintain Backwards Compatibility  
The script is now capable of parsing both modern, JSON-based \`.xpm\` files and legacy, direct-XML \`.xpm\` files (like those from firmware 1.x). This compatibility, especially within the \`process\_previews\_only\` function, is a critical feature. Any changes to file parsing logic \*\*must\*\* retain this dual-capability.

\#\#\# Rule \#5: The GUI Must Always Launch  
The script is a GUI application. No change, under any circumstances, should prevent the main \`App\` window from launching successfully. All fatal errors, especially \`NameError\` or \`AttributeError\` during initialization, are considered critical failures and must be fixed before submitting any code.

\#\#\# Rule \#6: Never Delete User Audio Files  
The script's functions must never delete \`.wav\`, \`.mp3\`, or any other non-temporary user audio files. The only files the script should be allowed to delete are its own temporary files (e.g., during a packaging process).

\#\# 4\. Integrating Additional Python Scripts (Modularity)

To maintain stability and organization, new complex features should be developed in \*\*separate Python script files\*\*. These files must then be integrated into the main \`Gemini wav_TO_XpmV2.py\` script without breaking any existing functionality.

\#\#\# Integration Protocol:

1\.  \*\*Create a Separate \`.py\` File\*\*: Develop your new feature (e.g., a new batch tool) in its own file (e.g., \`new\_feature\_tool.py\`). This file should contain the necessary logic and any new GUI windows (as \`Toplevel\` classes).  
2\.  \*\*Import into Main Script\*\*: In the main \`Gemini wav_TO_XpmV2.py\` script, import the necessary classes from your new file.  
    \`\`\`python  
    \# In Gemini wav_TO_XpmV2.py  
    from new\_feature\_tool import NewFeatureWindow  
    \`\`\`  
3\.  \*\*Add a GUI Entry Point\*\*: In the \`App\` class within the main script, add a new \`ttk.Button\` to the appropriate frame (e.g., "Advanced Tools" or "Utilities").  
4\.  \*\*Wire the Button\*\*: The new button's command should call the \`self.open\_window()\` method, passing the class name of your new tool's window as an argument. This ensures that the folder path is validated and that only one instance of the window can be opened at a time.  
    \`\`\`python  
    \# In the App class, inside a create\_\* method:  
    ttk.Button(frame, text="My New Tool", command=lambda: self.open\_window(NewFeatureWindow)).grid(...)  
    \`\`\`  
5\.  \*\*Strictly Adhere to Existing Patterns\*\*: The new tool's window class must inherit from \`tk.Toplevel\` and accept \`master\` as its first argument, just like the existing \`ExpansionDoctorWindow\` and other utility windows. This ensures it is properly parented to the main application window.
6\.  **Keep Function Signatures in Sync**: If you modify a function's parameters in any module, search the repository for that function name and update every call site. A mismatch in argument counts will cause runtime failures.

\*\*This modular approach is mandatory.\*\* It keeps the main script clean and ensures that new features can be developed and tested independently before being integrated, minimizing the risk of breaking the core application.

\#\# 5\. Key Architectural Points to Remember

\- \*\*\`InstrumentBuilder\` Class\*\*: This is the core engine for creating \`.xpm\` files. All logic for building the XML structure, handling layers, and applying creative parameters resides here.  
\- \*\*Dual XPM Formats\*\*: Remember the key difference between:  
  \- \*\*Modern XPMs (FW 2.x+)\*\*: Use a \`\<ProgramPads-v2.10\>\` (or \`\<ProgramPads\>\`) tag containing an escaped JSON string.  
  \- \*\*Legacy XPMs (FW 1.x)\*\*: Do not use a JSON block. Sample information is stored directly in \`\<Instrument\>\` \-\> \`\<Layer\>\` \-\> \`\<SampleName\>\` tags. The script must be able to read both.  
\- \*\*GUI Window Classes\*\*: Each tool (e.g., \`ExpansionDoctorWindow\`, \`BatchProgramEditorWindow\`) is a self-contained \`Toplevel\` window. This modularity should be maintained.

By following these guidelines, we can ensure the continued stability and reliability of the project.  
