"""Shared, conservative MIDI timing and chord recognition helpers."""

from collections import defaultdict

NOTE_NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
PATTERNS = {
    '': (0, 4, 7), 'm': (0, 3, 7), 'dim': (0, 3, 6),
    'aug': (0, 4, 8), 'sus2': (0, 2, 7), 'sus4': (0, 5, 7),
    '7': (0, 4, 7, 10), 'maj7': (0, 4, 7, 11),
    'm7': (0, 3, 7, 10), 'm7b5': (0, 3, 6, 10),
    'dim7': (0, 3, 6, 9), 'add9': (0, 2, 4, 7),
    'm(add9)': (0, 2, 3, 7), '6': (0, 4, 7, 9),
    'm6': (0, 3, 7, 9), '9': (0, 2, 4, 7, 10),
    'maj9': (0, 2, 4, 7, 11), 'm9': (0, 2, 3, 7, 10),
}


def recognize(notes):
    """Return (root pitch class, suffix, bass) only for an exact chord."""
    notes = sorted(set(notes))
    if not notes:
        return None
    pitches = {n % 12 for n in notes}
    bass = notes[0] % 12
    matches = [(root, suffix) for root in range(12)
               for suffix, pattern in PATTERNS.items()
               if {(root + i) % 12 for i in pattern} == pitches]
    if not matches:
        return None
    # Prefer root-position spelling when symmetric chords have multiple roots.
    root, suffix = next((match for match in matches if match[0] == bass), matches[0])
    return root, suffix, bass


def timed_notes(mid, mido):
    """Decode note spans using the global tempo map and independent track/channel keys."""
    events = []
    for track_id, track in enumerate(mid.tracks):
        tick = 0
        for msg in track:
            tick += msg.time
            events.append((tick, track_id, msg))
    events.sort(key=lambda item: (item[0], item[1]))
    tempo, previous_tick, seconds = 500000, 0, 0.0
    active = defaultdict(list)
    spans = []
    for tick, track_id, msg in events:
        seconds += mido.tick2second(tick - previous_tick, mid.ticks_per_beat, tempo)
        previous_tick = tick
        if msg.type == 'set_tempo':
            tempo = msg.tempo
            continue
        if msg.type not in ('note_on', 'note_off') or getattr(msg, 'channel', 0) == 9:
            continue
        key = (track_id, getattr(msg, 'channel', 0), msg.note)
        if msg.type == 'note_on' and msg.velocity > 0:
            active[key].append((seconds, msg.velocity))
        elif active[key]:
            start, velocity = active[key].pop(0)
            if seconds > start:
                spans.append((start, seconds, msg.note, velocity, track_id, key[1]))
    return sorted(spans)


def chord_groups(spans, window=0.06):
    """Separate onset clusters; use only notes belonging to a recognized chord."""
    groups = []
    for span in sorted(spans):
        if not groups or span[0] - groups[-1][0][0] > window:
            groups.append([span])
        else:
            groups[-1].append(span)
    result = []
    for group in groups:
        notes = sorted({span[2] for span in group})
        match = recognize(notes)
        if match:
            result.append((group, notes, match))
    return result
