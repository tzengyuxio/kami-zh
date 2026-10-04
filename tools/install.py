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

import tables

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


# KAMI.COM at 0x25f: mov dx,011d ("OPEN.EXE"); call exec; or ah,ah; jnz error
OPEN_EXEC = bytes.fromhex("ba1d01e8b0fe0ae47516")
# ...then mov dx,0126 ("MAIN.EXE"); call exec; or ah,ah; jnz error; or al,al; jnz quit
MAIN_EXEC = bytes.fromhex("ba2601e8a6fe0ae4750c0ac0750b")
HERO_BUFFER = 0xEC     # file offset of cs:01ec, the INT 65h AH=1/2 buffer


def skip_opening(com: Path) -> None:
    """Drop the OPEN.EXE step from KAMI.COM.

    KAMI.COM chains FMDRV -> OPEN.EXE -> MAIN.EXE -> END.EXE (END only when
    MAIN exits with code 0, i.e. after the last boss). Going through KAMI.COM
    matters: it installs the INT 65h handler MAIN.EXE needs -- running
    MAIN.EXE directly only gives a black screen. Renaming the OPEN slot to
    MAIN.EXE would run MAIN twice and so show the title again instead of the
    ending; NOP out the OPEN exec and its error check instead.
    """
    d = bytearray(com.read_bytes())
    i = d.find(OPEN_EXEC)
    if i < 0:
        sys.exit("KAMI.COM 裡找不到執行 OPEN.EXE 的程式碼")
    d[i:i + len(OPEN_EXEC)] = b"\x90" * len(OPEN_EXEC)
    com.write_bytes(bytes(d))


def ending_only(com: Path, out: Path, hero: bytes) -> None:
    """Write a KAMI.COM copy that plays only the ending (END.EXE).

    For watching the ending again: tools/dosbox/run.sh with
    KAMI_START=ENDING.COM. Works on the original or the skip_opening copy.
    END.EXE takes the hero's name (its U code) from a 21-byte buffer in
    KAMI.COM that MAIN.EXE fills through INT 65h AH=1 on the way out; with
    MAIN skipped, prefill it.
    """
    d = bytearray(com.read_bytes())
    if d.find(MAIN_EXEC) < 0:
        sys.exit("KAMI.COM 裡找不到執行 MAIN.EXE 的程式碼")
    for code in (OPEN_EXEC, MAIN_EXEC):
        i = d.find(code)
        if i >= 0:
            d[i:i + len(code)] = b"\x90" * len(code)
    d[HERO_BUFFER:HERO_BUFFER + 21] = hero[:20].ljust(21, b"\0")
    out.write_bytes(bytes(d))


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
    apply_in_place("translation/open_ui.tsv", "OPEN.EXE")
    apply_in_place("translation/end_ui.tsv", "END.EXE")

    # Name tables: fixed-stride records, 14 bytes of name each.
    for table in ("SDATA.CIM", "RPDATA.CIM"):
        run("tables.py", rel(GAME / table), "--table", table,
            "--glossary", "translation/glossary.tsv", "--out", rel(BUILD / table))

    # A new game starts from SDATA.CIM's own copy of the village table, so the
    # village names just patched into MAIN.EXE are carried across.
    sdata = bytearray((BUILD / "SDATA.CIM").read_bytes())
    tables.copy_village_names((BUILD / "MAIN.EXE").read_bytes(), sdata)
    (BUILD / "SDATA.CIM").write_bytes(bytes(sdata))

    # The hero's default name (person 0) for the ending-only launcher.
    hero = sdata[0x1372:0x1372 + 15].split(b"\0")[0]
    ending_only(BUILD / "KAMI.COM", BUILD / "ENDING.COM", hero)

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
