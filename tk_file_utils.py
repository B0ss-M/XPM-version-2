#!/usr/bin/env python3
"""Small helpers to normalize and safely call tkinter filedialogs.

This module normalizes filetypes (e.g. converts ';' or ',' separators to spaces)
and warns if called from a non-main thread (which can crash Tk on macOS).
"""
from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import filedialog
from typing import Iterable, List, Optional, Tuple


def _normalize_filetypes(filetypes: Optional[Iterable[Tuple[str, str]]]) -> Optional[List[Tuple[str, str]]]:
    if not filetypes:
        return None

    out: List[Tuple[str, str]] = []
    for entry in filetypes:
        if not entry:
            continue
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            label, pattern = entry[0], entry[1]
            if pattern is None:
                pat = ""
            elif isinstance(pattern, (list, tuple)):
                pat = " ".join(str(p) for p in pattern)
            else:
                pat = str(pattern).replace(';', ' ').replace(',', ' ')
            # collapse multiple whitespace
            pat = ' '.join(pat.split())
            out.append((label, pat))
        else:
            # unexpected form, try to stringify
            try:
                out.append((str(entry), '*.*'))
            except Exception:
                continue

    return out if out else None


def _warn_if_not_main_thread():
    if threading.current_thread() is not threading.main_thread():
        logging.warning('Tkinter filedialog called from non-main thread; this may crash on macOS.')


def askopenfilename(**kwargs):
    _warn_if_not_main_thread()
    if 'filetypes' in kwargs:
        kwargs['filetypes'] = _normalize_filetypes(kwargs.get('filetypes'))
    return filedialog.askopenfilename(**kwargs)


def askopenfilenames(**kwargs):
    _warn_if_not_main_thread()
    if 'filetypes' in kwargs:
        kwargs['filetypes'] = _normalize_filetypes(kwargs.get('filetypes'))
    return filedialog.askopenfilenames(**kwargs)


def asksaveasfilename(**kwargs):
    _warn_if_not_main_thread()
    if 'filetypes' in kwargs:
        kwargs['filetypes'] = _normalize_filetypes(kwargs.get('filetypes'))
    return filedialog.asksaveasfilename(**kwargs)


def askdirectory(**kwargs):
    _warn_if_not_main_thread()
    # directory dialogs do not use filetypes
    return filedialog.askdirectory(**kwargs)


def askopenfile(**kwargs):
    _warn_if_not_main_thread()
    if 'filetypes' in kwargs:
        kwargs['filetypes'] = _normalize_filetypes(kwargs.get('filetypes'))
    return filedialog.askopenfile(**kwargs)


def asksaveasfile(**kwargs):
    _warn_if_not_main_thread()
    if 'filetypes' in kwargs:
        kwargs['filetypes'] = _normalize_filetypes(kwargs.get('filetypes'))
    return filedialog.asksaveasfile(**kwargs)
