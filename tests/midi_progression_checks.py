"""Integration checks for MIDI timing, chord boundaries, and generated harmony."""
import tempfile
import unittest
from pathlib import Path

import mido

from scripts.midi_chord_analyzer import MIDIChordAnalyzer
from scripts.midi_to_progression import parse_midi_file
from scripts.music_theory_engine import MusicTheoryEngine, CHORD_INTERVALS


class ProgressionTests(unittest.TestCase):
    def test_tempo_inversion_and_chord_boundaries(self):
        midi = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        midi.tracks.append(track)
        for index, chord in enumerate(([64, 67, 72], [69, 72, 76],
                                       [65, 69, 72], [67, 71, 74])):
            if index == 1:
                track.append(mido.MetaMessage('set_tempo', tempo=1000000))
            for note in chord:
                track.append(mido.Message('note_on', note=note, velocity=90))
            for pos, note in enumerate(chord):
                track.append(mido.Message('note_off', note=note,
                                          time=480 if pos == 0 else 0))
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'progression.mid')
            midi.save(path)
            self.assertEqual([c['name'] for c in parse_midi_file(path)],
                             ['C/E', 'Am', 'F', 'G'])
            analysis = MIDIChordAnalyzer().analyze_midi_file(path)
            self.assertEqual(analysis.chord_symbols, ['C/E', 'Am', 'F', 'G'])
            self.assertEqual([round(c.start_time, 2) for c in analysis.chords],
                             [0, 0.5, 1.5, 2.5])

    def test_generator_uses_scale_chord_tones(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = MusicTheoryEngine(db_path=str(Path(directory) / 'chords.db'))
            for scale, allowed in [('major', {0, 2, 4, 5, 7, 9, 11}),
                                   ('minor', {0, 2, 3, 5, 7, 8, 10})]:
                for style in ('pop', 'jazz', 'ballad'):
                    chords = engine.generate_progression('C', scale, 8, style, 0.8)
                    self.assertEqual(len(chords), 8)
                    for chord in chords:
                        self.assertTrue({n % 12 for n in chord['notes']} <= allowed,
                                        (scale, style, chord))


if __name__ == '__main__':
    unittest.main()
