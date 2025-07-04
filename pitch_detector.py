import os
import argparse
import csv
import numpy as np
import librosa


def detect_pitch(path: str) -> str | None:
    """Return the detected note name for the given audio file."""
    y, sr = librosa.load(path, sr=None, mono=True)
    f0, _voiced_flag, _voiced_probs = librosa.pyin(
        y, sr=sr, fmin=librosa.note_to_hz('C1'), fmax=librosa.note_to_hz('C7')
    )
    if f0 is None:
        return None
    pitch_hz = np.nanmedian(f0)
    if np.isnan(pitch_hz):
        return None
    return librosa.hz_to_note(pitch_hz)


def process_folder(folder: str) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for root, _dirs, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(('.wav', '.aif', '.aiff')):
                path = os.path.join(root, file)
                try:
                    note = detect_pitch(path)
                except Exception as exc:
                    note = None
                    print(f"Error processing {path}: {exc}")
                results.append((path, note or 'N/A'))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect root notes for audio samples")
    parser.add_argument('folder', help='Folder with WAV/AIFF files')
    parser.add_argument('-o', '--output', help='Optional CSV output file')
    args = parser.parse_args()

    results = process_folder(args.folder)

    if args.output:
        with open(args.output, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['File', 'Note'])
            writer.writerows(results)
    else:
        for path, note in results:
            print(f"{path}\t{note}")


if __name__ == '__main__':
    main()
