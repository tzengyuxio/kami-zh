"""The game's 16-colour VGA palettes, measured from DOSBox-X screenshots.

DOSBox-X's raw screenshots are indexed PNGs carrying the live DAC, so they
record exactly what the game set. Every value is a multiple of 4 in the 6-bit
DAC, i.e. the game works in 4 bits per channel; entries are written here as
0xRGB with one hex digit per channel.

Colours 0-7 never change: they are the UI and the 3bpp graphics (FACEGRP's
blitter leaves plane 3 at 0, so those images only reach 0-7). Colours 8-15
are swapped per scene. See docs/formats.md section 2 for the evidence.
"""
from __future__ import annotations

BASE = [0x000, 0x348, 0xC40, 0x966, 0x571, 0x9BD, 0xDA4, 0xEED]

SCENES = {
    "field":   [0x322, 0x347, 0x832, 0xA53, 0x671, 0x8AC, 0xC93, 0xDCA],
    "village": [0x322, 0x347, 0x832, 0xA53, 0x671, 0x798, 0xC93, 0xDCA],
    "cave":    [0x100, 0xA40, 0xC70, 0xEA0, 0x950, 0x560, 0xC84, 0xFC0],
}


def to_rgb(v: int) -> tuple[int, int, int]:
    """0xRGB -> 8-bit RGB the way VGA shows it: 4 bits -> 6-bit DAC -> 8 bits."""
    def ch(n: int) -> int:
        dac = n << 2
        return (dac << 2) | (dac >> 4)
    return ch(v >> 8 & 0xF), ch(v >> 4 & 0xF), ch(v & 0xF)


def palette(scene: str = "field") -> list[tuple[int, int, int]]:
    return [to_rgb(v) for v in BASE + SCENES[scene]]
