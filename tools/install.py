#!/usr/bin/env python3
"""Copy the original game into build/ and apply every translation TSV.

    python3 tools/install.py

game/ stays pristine; everything lands in build/. Set SKIP_OPENING=0 to keep
KAMI.COM untouched (see below).

Only the standard library is used, so any python3 runs this -- the virtualenv
is needed by the graphics tools alone.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "game" / "KAMI"
BUILD = ROOT / "build" / "KAMI"


def rel(path: Path) -> str:
    """Repo-relative, forward-slashed -- the tools run with cwd=ROOT."""
    return path.relative_to(ROOT).as_posix()


def run(*args: str) -> None:
    """Run one of the sibling tools, letting its own output through."""
    subprocess.run([sys.executable, str(ROOT / "tools" / args[0]), *args[1:]],
                   cwd=ROOT, check=True)


def skip_opening(com: Path) -> None:
    """Point KAMI.COM's OPEN.EXE slot at MAIN.EXE.

    KAMI.COM chains FMDRV -> OPEN.EXE -> MAIN.EXE. Redirecting the OPEN slot
    skips the two-minute opening while still going through KAMI.COM, which is
    what installs the INT 65h handler MAIN.EXE needs -- running MAIN.EXE
    directly only gives a black screen.
    """
    d = bytearray(com.read_bytes())
    i = d.find(b"OPEN.EXE\x00")
    if i < 0:
        sys.exit("KAMI.COM 裡找不到 OPEN.EXE 字串")
    d[i:i + 8] = b"MAIN.EXE"
    com.write_bytes(bytes(d))


def apply_in_place(tsv: str, target: str) -> None:
    """In-place string patch: the translation must fit the slot it overwrites.

    patch.py reads a pristine copy and writes the patched one, so successive
    passes over the same file go through a temporary original.
    """
    dest = BUILD / target
    fd, tmp = tempfile.mkstemp(prefix="kami-patch-")
    os.close(fd)
    try:
        shutil.copyfile(dest, tmp)
        run("patch.py", "apply", "--tsv", tsv, "--target", tmp, "--out", rel(dest))
    finally:
        os.unlink(tmp)


def main() -> None:
    if not (GAME / "MAIN.EXE").is_file():
        sys.exit(f"找不到遊戲原檔，請先把遊戲解壓到 {GAME}")

    BUILD.mkdir(parents=True, exist_ok=True)
    for src in sorted(GAME.iterdir()):
        if src.is_file():
            shutil.copy2(src, BUILD / src.name)

    if os.environ.get("SKIP_OPENING", "1") == "1":
        skip_opening(BUILD / "KAMI.COM")

    apply_in_place("translation/main_ui.tsv", "MAIN.EXE")
    apply_in_place("translation/trial_startmenu.tsv", "MAIN.EXE")
    apply_in_place("translation/open_ui.tsv", "OPEN.EXE")

    # Name tables: fixed-stride records, 14 bytes of name each.
    for table in ("SDATA.CIM", "RPDATA.CIM"):
        run("tables.py", rel(GAME / table), "--table", table,
            "--glossary", "translation/glossary.tsv", "--out", rel(BUILD / table))

    # Story text: EVENT.DAT is rebuilt from scratch, so translations may be any
    # length. The block offsets this moves live in MAIN.EXE, which is why the
    # already-patched MAIN.EXE goes in and comes back out.
    run("event.py", "--event", rel(GAME / "EVENT.DAT"), "--main", rel(BUILD / "MAIN.EXE"),
        "apply", "--tsv", "translation/event.tsv",
        "--out-event", rel(BUILD / "EVENT.DAT"), "--out-main", rel(BUILD / "MAIN.EXE"))

    # MAIN.EXE is patched in place and must keep its size; EVENT.DAT may not.
    before = (GAME / "MAIN.EXE").stat().st_size
    after = (BUILD / "MAIN.EXE").stat().st_size
    if before != after:
        sys.exit(f"MAIN.EXE 大小改變了: {before} -> {after}")
    print(f"build/ 已就緒 (MAIN.EXE {after} bytes, "
          f"EVENT.DAT {(BUILD / 'EVENT.DAT').stat().st_size} bytes)")


if __name__ == "__main__":
    main()
