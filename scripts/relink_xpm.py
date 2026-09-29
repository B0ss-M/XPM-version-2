"""CLI wrapper around xpm_relinker.

Usage examples (dry-run):
    python3 scripts/relink_xpm.py /path/to/file.xpm --search /path/to/samples --out report.csv --dry-run

To apply relinks for high confidence matches:
    python3 scripts/relink_xpm.py file.xpm --search samples/ --out report.csv --apply --threshold 0.85
"""
import argparse
import logging
import sys
from pathlib import Path

from xpm_relinker import suggest_relinks_for_xpm, write_report_csv, apply_relinks, repair_keygroups


def main(argv=None):
    parser = argparse.ArgumentParser(description='Suggest and apply relinks for an XPM file')
    parser.add_argument('xpm', help='Path to XPM file')
    parser.add_argument('--search', '-s', action='append', required=True, help='Directory to search for audio candidates (can be repeated)')
    parser.add_argument('--out', '-o', default='relink_report.csv', help='CSV report output path')
    parser.add_argument('--apply', action='store_true', help='Apply relinks above threshold (default is dry-run)')
    parser.add_argument('--threshold', type=float, default=0.8, help='Confidence threshold to apply relinks')
    parser.add_argument('--top-n', type=int, default=3, help='Top N candidates per missing sample')
    parser.add_argument('--fix-keygroups', action='store_true', help='Repair KeygroupNumKeygroups and padToInstrument (dry-run unless --apply)')
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    xpm_path = args.xpm
    search_dirs = args.search

    report = suggest_relinks_for_xpm(xpm_path, search_dirs, top_n=args.top_n)
    write_report_csv(report, args.out)

    applied = apply_relinks(report, threshold=args.threshold, dry_run=not args.apply)
    print(f"Report written to {args.out}. Dry-run applied {len(applied)} candidates (apply flag={args.apply}).")

    if args.fix_keygroups:
        res = repair_keygroups(xpm_path, dry_run=not args.apply)
        print('Keygroup repair result:', res)


if __name__ == '__main__':
    main()
