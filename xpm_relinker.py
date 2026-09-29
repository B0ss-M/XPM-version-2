"""Fuzzy relinker for XPM files.

Provides a safe, non-destructive dry-run that suggests candidate audio files
to replace missing SampleFile entries in XPMs. Includes an optional apply
function that modifies XPMs only when candidate confidence exceeds a
configurable threshold and always creates a timestamped backup.

This module avoids heavy optional dependencies; it uses the standard library
for similarity scoring and WAV duration extraction. If `soundfile` or
`librosa` are available, durations will be more accurate.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape, unescape as xml_unescape
import json
import difflib
import wave
import contextlib
import time
import csv
import logging
from xpm_utils import load_program_pads, write_program_pads
from typing import List, Dict, Any, Optional, Tuple

try:
    import soundfile as sf  # type: ignore
    SOUNDFILE = True
except Exception:
    sf = None
    SOUNDFILE = False

try:
    import librosa  # type: ignore
    LIBROSA = True
except Exception:
    librosa = None
    LIBROSA = False


LOG = logging.getLogger("xpm_relinker")

# Common audio extensions
AUDIO_EXTS = ('.wav', '.aiff', '.aif', '.flac', '.mp3', '.m4a', '.ogg')


def _get_wav_duration(path: str) -> Optional[float]:
    try:
        if path.lower().endswith('.wav'):
            with contextlib.closing(wave.open(path, 'rb')) as w:
                frames = w.getnframes()
                rate = w.getframerate()
                return frames / float(rate) if rate > 0 else None
        if SOUNDFILE:
            info = sf.info(path)
            return float(info.frames) / float(info.samplerate)
        if LIBROSA:
            y, sr = librosa.load(path, sr=None, mono=True)
            return len(y) / float(sr) if sr > 0 else None
    except Exception as e:
        LOG.debug("Could not get duration for %s: %s", path, e)
    return None


def collect_candidates(search_dirs: List[str]) -> List[Dict[str, Any]]:
    """Walk search_dirs and collect audio candidates with metadata.

    Returns list of dicts: {path, basename, size, duration}
    """
    candidates: List[Dict[str, Any]] = []
    seen = set()
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                    p = os.path.join(root, f)
                    if p in seen:
                        continue
                    seen.add(p)
                    try:
                        size = os.path.getsize(p)
                    except Exception:
                        size = 0
                    duration = _get_wav_duration(p)
                    candidates.append({
                        'path': p,
                        'basename': os.path.basename(p).lower(),
                        'size': size,
                        'duration': duration,
                    })
    LOG.info("Collected %d audio candidates from %d search dirs", len(candidates), len(search_dirs))
    return candidates


def _name_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _size_similarity(a: int, b: int) -> float:
    if a <= 0 or b <= 0:
        return 0.0
    diff = abs(a - b)
    return max(0.0, 1.0 - (diff / max(a, b)))


def _duration_similarity(a: Optional[float], b: Optional[float]) -> float:
    if not a or not b or a <= 0 or b <= 0:
        return 0.0
    diff = abs(a - b)
    return max(0.0, 1.0 - (diff / max(a, b)))


def suggest_relinks_for_xpm(xpm_path: str, search_dirs: List[str], top_n: int = 3) -> Dict[str, Any]:
    """Return suggestions for missing SampleFile entries.

    The returned dict contains:
      - xpm_path
      - suggestions: list of {missing, element_xpath, candidates: [{path,score,components}]}
      - candidates_index: internal candidate list
    """
    tree = ET.parse(xpm_path)
    root = tree.getroot()
    xpm_dir = os.path.dirname(xpm_path)

    # Find SampleFile elements
    sample_elements = []
    for elem in root.findall('.//SampleFile'):
        text = elem.text or ''
        sample_elements.append((elem, text.strip()))

    candidates = collect_candidates(search_dirs)

    suggestions = []

    for elem, ref in sample_elements:
        ref_text = ref
        # normalize
        ref_base = os.path.basename(ref_text).lower()
        # if already exists on disk (relative to xpm) skip
        ref_path = ref_text
        if not os.path.isabs(ref_path):
            ref_path = os.path.join(xpm_dir, ref_path)
        if os.path.exists(ref_path):
            continue

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for c in candidates:
            name_sim = _name_similarity(ref_base, c['basename'])
            size_sim = _size_similarity(0, c['size'])  # no reliable ref size available
            dur_sim = _duration_similarity(None, c['duration'])

            # Combine weights; name is primary
            score = min(1.0, 0.6 * name_sim + 0.25 * size_sim + 0.15 * dur_sim)

            # Slight boost for exact basename match
            if ref_base == c['basename']:
                score = min(1.0, score + 0.3)

            scored.append((score, {
                'path': c['path'],
                'basename': c['basename'],
                'size': c['size'],
                'duration': c['duration'],
                'score': score,
                'components': {'name_sim': name_sim, 'size_sim': size_sim, 'dur_sim': dur_sim},
            }))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [s[1] for s in scored[:top_n]]
        suggestions.append({
            'missing': ref,
            'element': elem,
            'candidates': top,
        })

    return {
        'xpm_path': xpm_path,
        'suggestions': suggestions,
        'candidates_index_count': len(candidates),
    }


def write_report_csv(report: Dict[str, Any], out_csv: str) -> None:
    """Write a flat CSV report for manual review."""
    rows = []
    for s in report['suggestions']:
        missing = s['missing']
        for cand in s['candidates']:
            rows.append({
                'xpm': report['xpm_path'],
                'missing': missing,
                'candidate': cand['path'],
                'score': f"{cand['score']:.3f}",
                'name_sim': f"{cand['components']['name_sim']:.3f}",
                'size': cand['size'],
                'duration': cand['duration'] or '',
            })

    fieldnames = ['xpm', 'missing', 'candidate', 'score', 'name_sim', 'size', 'duration']
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    LOG.info('Wrote relink report to %s (%d rows)', out_csv, len(rows))


def apply_relinks(report: Dict[str, Any], threshold: float = 0.8, dry_run: bool = True) -> List[Dict[str, Any]]:
    """Apply relinks for candidates meeting the threshold.

    Returns list of applied changes: {xpm, missing, chosen, score, backup}
    """
    applied = []
    xpm_path = report['xpm_path']
    tree = ET.parse(xpm_path)
    root = tree.getroot()
    timestamp = int(time.time())
    backup_path = f"{xpm_path}.bak.{timestamp}"

    for s in report['suggestions']:
        missing = s['missing']
        if not s['candidates']:
            continue
        best = s['candidates'][0]
        score = best['score']
        if score < threshold:
            continue

        # Update element text
        elem = s['element']
        new_path = best['path']

        applied.append({
            'xpm': xpm_path,
            'missing': missing,
            'chosen': new_path,
            'score': score,
            'backup': backup_path,
        })

        if not dry_run:
            # backup once
            if not os.path.exists(backup_path):
                try:
                    import shutil
                    shutil.copy2(xpm_path, backup_path)
                except Exception as e:
                    LOG.error('Could not create backup %s: %s', backup_path, e)
            elem.text = new_path

    if not dry_run and applied:
        tree.write(xpm_path, encoding='utf-8', xml_declaration=True)
        LOG.info('Applied %d relinks to %s (backup: %s)', len(applied), xpm_path, backup_path)
    else:
        LOG.info('Dry-run: %d candidate relinks would be applied to %s', len(applied), xpm_path)

    return applied


def repair_keygroups(xpm_path: str, dry_run: bool = True) -> Dict[str, Any]:
    """Repair Keygroup count and padToInstrument mapping in an XPM file.

    - Ensures <KeygroupNumKeygroups> equals actual number of <Instrument> entries.
    - If ProgramPads JSON contains padToInstrument with incorrect size, rebuild it.

    Returns a dict describing applied or suggested changes.
    """
    tree = ET.parse(xpm_path)
    root = tree.getroot()

    instruments = root.findall('.//Instruments/Instrument')
    actual_kg_count = len(instruments)

    changes = {
        'xpm': xpm_path,
        'actual_kg_count': actual_kg_count,
        'kg_declared': None,
        'kg_changed': False,
        'padToInstrument_changed': False,
        'backup': None,
    }

    kg_elem = root.find('.//KeygroupNumKeygroups')
    if kg_elem is not None and kg_elem.text is not None:
        try:
            declared = int(kg_elem.text)
        except Exception:
            declared = None
        changes['kg_declared'] = declared
        if declared != actual_kg_count:
            changes['kg_changed'] = True
            if not dry_run:
                kg_elem.text = str(actual_kg_count)

    # Try to find ProgramPads and adjust padToInstrument if present
    pads_elem = next((elem for elem in root.iter() if isinstance(elem.tag, str)
                      and (elem.tag == 'ProgramPads' or elem.tag.startswith('ProgramPads-v'))), None)
    if pads_elem is not None and pads_elem.text:
        data, payload = load_program_pads(pads_elem)
        pti = payload.get('padToInstrument') if payload else None
        if isinstance(pti, dict) and len(pti) != actual_kg_count:
            changes['padToInstrument_changed'] = True
            if not dry_run:
                payload['padToInstrument'] = {str(i): i for i in range(actual_kg_count)}
                write_program_pads(pads_elem, data)

    if not dry_run and (changes['kg_changed'] or changes['padToInstrument_changed']):
        # create backup
        try:
            import shutil
            timestamp = int(time.time())
            backup = f"{xpm_path}.kgfix.bak.{timestamp}"
            shutil.copy2(xpm_path, backup)
            changes['backup'] = backup
        except Exception as e:
            LOG.error('Failed to create backup for %s: %s', xpm_path, e)

        tree.write(xpm_path, encoding='utf-8', xml_declaration=True)
        LOG.info('Repaired keygroup counts for %s (backup: %s)', xpm_path, changes['backup'])
    else:
        LOG.info('Dry-run keygroup repair for %s: %s', xpm_path, {k: changes[k] for k in ('kg_changed','padToInstrument_changed','kg_declared','actual_kg_count')})

    return changes


if __name__ == '__main__':
    print('xpm_relinker module - import and use via scripts/relink_xpm.py')
