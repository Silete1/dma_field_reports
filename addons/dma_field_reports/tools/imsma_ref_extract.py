#!/usr/bin/env python3
"""Build an IMSMA reference package for DMA Field Reports from an IMSMA NG backup.

Usage:
    python imsma_ref_extract.py --backup <Backup_YYYY_MM_DD_...\\Dump.sql | folder of copy_*.txt> --out imsma_ref_<date>.zip

The package holds no field-report contents, only lists (forms, custom fields and
their values, gazetteer, locations, organisations, task ids, ids in use, report
ids and statuses). It still comes from IMSMA: keep it off git and public places.
Standard library only.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services"))
import refdata  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--backup", required=True, help="Dump.sql of an IMSMA backup, or a folder of copy_<table>.txt files")
    p.add_argument("--out", required=True, help="package zip to write")
    p.add_argument("--dump-date", help="YYYY-MM-DD of the backup (default: from the Backup_YYYY_MM_DD folder name)")
    a = p.parse_args(argv)
    if not os.path.exists(a.backup):
        p.error(f"{a.backup} does not exist")
    t0 = time.time()
    out, manifest = refdata.build_from_backup(a.backup, a.dump_date)
    with open(a.out, "wb") as f:
        manifest = refdata.write_package(out, manifest, f)
    for name, info in manifest["files"].items():
        print(f"  {name:20} {info['rows']:>8} rows")
    print(f"written {a.out} in {time.time() - t0:.0f}s (dump date {manifest.get('dump_date') or 'unknown'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
