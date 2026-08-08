"""Translate raw terminal input into reusable picker actions."""

from __future__ import annotations

import os
import sys
import termios
import tty


def read_picker_key() -> str:
    """Read one raw key and translate arrows, vim keys, and picker actions."""
    fd = sys.stdin.fileno()
    original = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        first = os.read(fd, 1)
        if first in {b"\r", b"\n"}:
            return "enter"
        if first == b"k":
            return "up"
        if first == b"j":
            return "down"
        if first == b" ":
            return "toggle"
        if first == b"n":
            return "new"
        if first == b"q":
            return "quit"
        if first == b"\x1b":
            second = os.read(fd, 1)
            if second == b"[":
                third = os.read(fd, 1)
                if third == b"A":
                    return "up"
                if third == b"B":
                    return "down"
            return "escape"
        return ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original)
