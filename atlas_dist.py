#!/usr/bin/env python3
"""
atlas_dist.py  -  bundles for a new install, of the Reader or of Word Atlas

The Reader needs two things to run somewhere else: its program files
(nine small Python files beside the program) and a dataset (a .wadb,
which atlas_pack.py makes from reports/results.db).  Word Atlas
itself needs its source files, the text backup of metadata.db (the
database itself is rebuilt from the backup), the cross references,
and then the builds that only run where bibles.db and the Greek and
Hebrew data are.  This module makes and opens the zip files that
carry each, and says what a fresh install still has to build.

    python3 atlas_dist.py reader [--wadb FILE] [--out ZIP] [--guest-key] [--reader DIR]
        a zip of the Reader's files with a dataset in its sample folder
        (the newest .wadb under reports/ unless --wadb says which) and,
        with --guest-key, the guest_key.dat beside the Reader; the
        Reader's folder is word_atlas_reader beside this one unless
        --reader says where

    python3 atlas_dist.py atlas [--out ZIP]
        a zip of Word Atlas's source and text files, metadata_backup.sql
        and cross_references.db: everything git carries, and the two
        data files a fresh copy wants first

    python3 atlas_dist.py unpack ZIP FOLDER [--force]
        open a bundle into a folder (made if it does not exist; files
        already there are left alone unless --force)

    python3 atlas_dist.py check [FOLDER]
        what an install has and what it still has to make, with the
        command for each, for this folder or another

    python3 atlas_dist.py list ZIP
        what a bundle holds

The bundles are zip files any unzip program opens, so a reader with
no Python at all can still see what is inside.  Nothing copyrighted
goes into either: the Reader bundle carries the pages' counts and
words, the atlas bundle the program and the open data it cites.
"""

import glob
import os
import sys
import time
import zipfile

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(PROGRAM_DIR)
READER_DIR = os.path.join(PARENT_DIR, "word_atlas_reader")
REPORTS_DIR = os.path.join(PROGRAM_DIR, "reports")

# The Reader's files, as its README lists them
READER_FILES = ["word_atlas_reader.py", "reader_data.py", "reader_claude.py", "reader_guest.py",
                "reader_questions.py", "reader_help.py", "atlas_report.py", "atlas_results.py",
                "atlas_listed.py", "test_reader.py", "word_atlas_reader.spec", "README.md", "requirements.txt"]

# Word Atlas's data files that are not source and not built: carried in the bundle
ATLAS_DATA = ["metadata_backup.sql", "cross_references.db", "LICENSE", "requirements.txt"]
# Built or copyrighted or large: never in the bundle (git ignores them too)
ATLAS_SKIP = {"atlas.db", "lxx.db", "bibles.db", "metadata.db", "translations.db", "translations_index.db",
              "sefaria_links.db", "richness_cache.json", "test_bibles.db", "lxx_backup.db", "metadata_test_backup.db"}
ATLAS_SKIP_DIRS = {"__pycache__", "reports", "builds", "venv", "data", "strongs3-master", "Sept With Strongs",
                   "Claude outputs", ".git"}

# What a Word Atlas install has to have or make, in the order it is made
ATLAS_NEEDS = [
    ("metadata.db", "python3 atlas_backup.py restore", "the catalogue, rebuilt from metadata_backup.sql"),
    ("bibles.db (or Bible Search Lite's)", "copy bibles.db beside the program, or install Bible Search Lite",
     "the King James text with Strong's numbers; the atlas is built from it"),
    ("atlas.db", "python3 build_atlas.py", "the atlas itself, about a minute"),
    ("lxx.db", "python3 build_lxx.py, then build_gnt.py and build_tahot.py",
     "the Septuagint layer, from the Rahlfs, TAGNT and TAHOT data"),
    ("cross_references.db", "(in the bundle; else export the table from bibles.db)", "the listed column"),
    ("sefaria_links.db", "python3 sefaria_links.py hebrew, import, pairs", "the cited column (needs the Sefaria export)"),
    ("translations_index.db", "python3 atlas_translations.py maps, survey --write, build",
     "the translations columns (needs the translations in bibles.db)"),
    ("reports/results.db", "python3 atlas_query.py dossier all --results", "the results database the questions read"),
]


def newest_wadb():
    """The newest .wadb under reports/, or None."""
    files = sorted(glob.glob(os.path.join(REPORTS_DIR, "*.wadb")), key=os.path.getmtime)
    return files[-1] if files else None


def reader_bundle(wadb=None, out=None, guest_key=False, reader_dir=READER_DIR, log=print):
    """Zip the Reader's files with a dataset in sample/; returns the zip's path."""
    if not os.path.exists(os.path.join(reader_dir, "word_atlas_reader.py")):
        raise SystemExit(f"the Reader was not found at {reader_dir}")
    wadb = wadb or newest_wadb()
    if not wadb or not os.path.exists(wadb):
        raise SystemExit("no .wadb found under reports/: pack one with  python3 atlas_pack.py")
    version = "0"
    with open(os.path.join(reader_dir, "word_atlas_reader.py"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("VERSION"):
                version = line.split('"')[1]
                break
    out = out or os.path.join(REPORTS_DIR, f"word_atlas_reader_{version}_{time.strftime('%Y-%m-%d')}.zip")
    missing = [n for n in READER_FILES if not os.path.exists(os.path.join(reader_dir, n))]
    if missing:
        log(f"  not in the Reader's folder, left out: {', '.join(missing)}")
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in READER_FILES:
            path = os.path.join(reader_dir, name)
            if os.path.exists(path):
                z.write(path, "word_atlas_reader/" + name)
        z.write(wadb, "word_atlas_reader/sample/" + os.path.basename(wadb))
        key = os.path.join(reader_dir, "guest_key.dat")
        if guest_key:
            if os.path.exists(key):
                z.write(key, "word_atlas_reader/guest_key.dat")
                log("  guest_key.dat included: delete the key in the console on its end date")
            else:
                log("  --guest-key asked for but no guest_key.dat beside the Reader (python3 reader_guest.py make KEY DAYS)")
        z.writestr("word_atlas_reader/START.txt",
                   "Word Atlas Reader\n\nInstall Python 3.9 or later and PyQt6 (pip install PyQt6), then run\n\n"
                   "    python3 word_atlas_reader.py\n\nand open the dataset in the sample folder "
                   f"({os.path.basename(wadb)}).  README.md says the rest.\n")
    log(f"wrote {out} ({os.path.getsize(out) / 1e6:.1f} MB) with {os.path.basename(wadb)}")
    return out


def atlas_files(program_dir=PROGRAM_DIR):
    """The files of a Word Atlas source bundle: every .py and .md and the data files, no builds."""
    out = []
    for root, dirs, files in os.walk(program_dir):
        dirs[:] = [d for d in dirs if d not in ATLAS_SKIP_DIRS]
        for name in sorted(files):
            if name in ATLAS_SKIP or name.endswith((".pyc", ".db-journal", ".bak", ".tmp")):
                continue
            rel = os.path.relpath(os.path.join(root, name), program_dir)
            if root == program_dir and not (name.endswith((".py", ".md", ".txt", ".tsv", ".spec")) or name in ATLAS_DATA
                                            or name.startswith(".gitignore")):
                continue
            out.append(rel)
    return out


def atlas_bundle(out=None, program_dir=PROGRAM_DIR, log=print):
    """Zip Word Atlas's sources and open data files; returns the zip's path."""
    from atlas_pages import VERSION
    out = out or os.path.join(REPORTS_DIR, f"word_atlas_{VERSION}_source_{time.strftime('%Y-%m-%d')}.zip")
    files = atlas_files(program_dir)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in files:
            z.write(os.path.join(program_dir, rel), "word_atlas/" + rel)
        z.writestr("word_atlas/START.txt",
                   "Word Atlas\n\nUnpack beside a copy of Bible Search Lite (or put bibles.db in this folder), then\n\n"
                   "    pip install PyQt6\n    python3 atlas_backup.py restore\n    python3 build_atlas.py\n"
                   "    python3 word_atlas.py\n\nor open python3 atlas_workbench.py and use its Install menu, which "
                   "says what is still to build.  README.md and WORD_ATLAS_MANUAL.md say the rest.\n")
    log(f"wrote {out} ({os.path.getsize(out) / 1e6:.1f} MB) with {len(files)} files")
    for name in ("metadata_backup.sql", "cross_references.db"):
        if name not in files:
            log(f"  {name} was not found and is not in the bundle")
    return out


def unpack(zip_path, folder, force=False, log=print):
    """Open a bundle into a folder; files already there are kept unless force."""
    if not zipfile.is_zipfile(zip_path):
        raise SystemExit(f"{zip_path} is not a zip file")
    os.makedirs(folder, exist_ok=True)
    written = kept = 0
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            # Paths are kept inside the folder whatever the zip says
            rel = os.path.normpath(info.filename)
            if rel.startswith("..") or os.path.isabs(rel):
                continue
            target = os.path.join(folder, rel)
            if os.path.exists(target) and not force:
                kept += 1
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())
            written += 1
    log(f"unpacked {written} files into {folder}" + (f"; {kept} already there were left alone (--force replaces them)"
                                                     if kept else ""))
    top = sorted({os.path.normpath(i.filename).split(os.sep)[0] for i in zipfile.ZipFile(zip_path).infolist()})
    log("  top folder: " + ", ".join(top))
    return written


def check(folder=PROGRAM_DIR, log=print):
    """What an install has, and the command for each thing it lacks."""
    log(f"Word Atlas install at {folder}")
    program = os.path.exists(os.path.join(folder, "word_atlas.py"))
    log(f"  program files: {'present' if program else 'MISSING (unpack the source bundle here, or git clone)'}")
    for name, how, what in ATLAS_NEEDS:
        plain = name.split(" ")[0]
        path = os.path.join(folder, plain)
        present = os.path.exists(path)
        if plain == "bibles.db" and not present:
            try:
                sys.path.insert(0, folder)
                import atlas_text
                present = os.path.exists(atlas_text.find_database())
            except Exception:           # noqa: BLE001
                present = False
        size = f" ({os.path.getsize(path) / 1e6:.0f} MB)" if present and os.path.exists(path) else ""
        log(f"  {name:34} {'present' + size if present else 'to make:  ' + how}    [{what}]")
    reader = os.path.join(os.path.dirname(folder), "word_atlas_reader")
    log(f"  the Reader beside it: {'present' if os.path.exists(os.path.join(reader, 'word_atlas_reader.py')) else 'not found'}")
    wadb = newest_wadb() if folder == PROGRAM_DIR else None
    log(f"  newest dataset for the Reader: {os.path.basename(wadb) if wadb else 'none (python3 atlas_pack.py)'}")


def list_bundle(zip_path, log=print):
    with zipfile.ZipFile(zip_path) as z:
        total = 0
        for info in z.infolist():
            if not info.is_dir():
                total += info.file_size
                log(f"  {info.file_size / 1e6:8.2f} MB  {info.filename}")
        log(f"{len(z.infolist())} entries, {total / 1e6:.1f} MB unpacked, {os.path.getsize(zip_path) / 1e6:.1f} MB zipped")


def main(argv):
    args = argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = args[0]
    opts = {a: args[i + 1] for i, a in enumerate(args) if a.startswith("--") and i + 1 < len(args) and not args[i + 1].startswith("--")}
    flags = {a for a in args if a.startswith("--")}
    if cmd == "reader":
        reader_bundle(wadb=opts.get("--wadb"), out=opts.get("--out"), guest_key="--guest-key" in flags,
                      reader_dir=os.path.expanduser(opts.get("--reader", READER_DIR)))
    elif cmd == "atlas":
        atlas_bundle(out=opts.get("--out"))
    elif cmd == "unpack" and len(args) >= 3:
        unpack(args[1], os.path.expanduser(args[2]), force="--force" in flags)
    elif cmd == "check":
        check(os.path.expanduser(args[1]) if len(args) > 1 and not args[1].startswith("--") else PROGRAM_DIR)
    elif cmd == "list" and len(args) >= 2:
        list_bundle(args[1])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
