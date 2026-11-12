"""Build dual_text_mod.rpa from the sources in dual_text_mod/.

    python tools/build.py --renpy "C:/path/to/renpy-8.2.1/renpy.exe"

Ren'Py only reads the compiled .rpyc files inside an archive, so the sources are compiled first.
Compile with the OLDEST Ren'Py 8 you want to support: newer versions read older .rpyc files, but
an 8.2.1 game cannot read .rpyc files compiled by 8.5.x. Any Ren'Py 8.2.1 SDK or game executable
works (a game's .exe accepts another project folder as its first argument).

The script compiles in a temporary project, packs the archive and then checks it: every .rpy must
be inside together with a .rpyc compiled from exactly that source.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpa  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(REPO, "dual_text_mod")
MOD_DIR = "dual_text_mod"

# Ren'Py 8.3+ mixes a magic string into the .rpyc source digest; 8.2 and older use plain MD5.
RPYC_DIGEST_MAGICS = (b"", b"_2025-07-06")


def renpy_version(exe):
    path = os.path.join(os.path.dirname(os.path.abspath(exe)), "renpy", "vc_version.py")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("version ="):
                    return line.split("=", 1)[1].strip().strip("'\"")
    except OSError:
        pass
    return "unknown"


def source_files():
    names = sorted(n for n in os.listdir(SOURCE) if not n.endswith(".rpyc") and not n.startswith("."))
    if not any(n.endswith(".rpy") for n in names):
        sys.exit("no .rpy files in %s" % SOURCE)
    return names


def compile_sources(exe, names, workdir):
    project = os.path.join(workdir, "project")
    game = os.path.join(project, "game")
    mod = os.path.join(game, MOD_DIR)
    os.makedirs(mod)
    with open(os.path.join(game, "script.rpy"), "w", encoding="utf-8") as f:
        f.write("label start:\n    return\n")
    for name in names:
        shutil.copy2(os.path.join(SOURCE, name), os.path.join(mod, name))

    print("compiling with %s (Ren'Py %s)" % (exe, renpy_version(exe)))
    subprocess.run([exe, project, "compile"], timeout=600, check=False)

    for report in ("traceback.txt", "errors.txt"):
        path = os.path.join(project, report)
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                sys.exit("Ren'Py reported a problem (%s):\n%s" % (report, f.read()))
    return game


def archive_names(names):
    rv = []
    for name in names:
        rv.append(MOD_DIR + "/" + name)
        if name.endswith(".rpy"):
            rv.append(MOD_DIR + "/" + name + "c")
    return rv


def check(path, names):
    files = rpa.read(path)
    problems = []
    for name in names:
        member = MOD_DIR + "/" + name
        with open(os.path.join(SOURCE, name), "rb") as f:
            source = f.read()
        if files.get(member) != source:
            problems.append("%s differs from the source" % member)
        if name.endswith(".rpy"):
            compiled = files.get(member + "c")
            if compiled is None:
                problems.append("%sc is missing" % member)
                continue
            digests = [hashlib.md5(source + magic).digest() for magic in RPYC_DIGEST_MAGICS]
            if compiled[-16:] not in digests:
                problems.append("%sc was not compiled from this source" % member)
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--renpy", required=True, help="Ren'Py executable used to compile (use 8.2.1)")
    parser.add_argument("--out", default=os.path.join(REPO, "dual_text_mod.rpa"), help="archive to write")
    args = parser.parse_args()

    names = source_files()
    workdir = tempfile.mkdtemp(prefix="dual-text-build-")
    try:
        game = compile_sources(args.renpy, names, workdir)
        packed = archive_names(names)
        missing = [n for n in packed if not os.path.exists(os.path.join(game, n))]
        if missing:
            sys.exit("compiling did not produce: %s" % ", ".join(missing))
        rpa.write(args.out, game, packed)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    problems = check(args.out, names)
    if problems:
        sys.exit("archive check failed:\n  " + "\n  ".join(problems))
    print("wrote %s (%d bytes, %d files), sources and .rpyc match" % (args.out, os.path.getsize(args.out), len(packed)))


if __name__ == "__main__":
    main()
