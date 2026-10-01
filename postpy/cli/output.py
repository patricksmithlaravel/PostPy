"""
Helpers for printing untrusted text to the terminal.
"""

import re

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def printable(value: str) -> str:
    """Show control characters as ``\\xNN`` so text cannot drive the terminal.

    Response bodies and collection fields can contain escape sequences that
    rewrite earlier output, retitle the window or set the clipboard. Tabs and
    newlines are kept, and Windows line endings are normalized first.
    """
    return _CONTROL.sub(
        lambda m: f"\\x{ord(m.group()):02x}", value.replace("\r\n", "\n")
    )
