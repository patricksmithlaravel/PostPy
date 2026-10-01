import pytest

from postpy.cli.output import printable


@pytest.mark.parametrize(
    "value, expected",
    [
        ("plain text\twith tab\nand newline", "plain text\twith tab\nand newline"),
        ("crlf\r\nline", "crlf\nline"),
        ("lone\rcarriage", "lone\\x0dcarriage"),
        ("\x1b[31mred\x1b[0m", "\\x1b[31mred\\x1b[0m"),
        ("osc\x1b]52;c;ZGF0YQ==\x07", "osc\\x1b]52;c;ZGF0YQ==\\x07"),
        ("c1\x9b2K\x85", "c1\\x9b2K\\x85"),
        ("nul\x00del\x7f", "nul\\x00del\\x7f"),
        ("unicode ✓ café", "unicode ✓ café"),
    ],
)
def test_printable(value, expected):
    assert printable(value) == expected
