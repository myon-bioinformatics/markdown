from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_exports() -> None:
    for name in (
        "calendar_to_markdown",
        "platform_to_markdown",
        "email_to_markdown",
        "markdown_to_email",
        "markdown_to_man",
    ):
        assert name in md.__all__


# --- calendar ---------------------------------------------------------------

def test_calendar_month_table_is_deterministic_english() -> None:
    out = md.calendar_to_markdown(2026, 9)
    assert out.startswith("## September 2026\n\n| Mon | Tue | Wed | Thu | Fri | Sat | Sun |\n")
    assert "|  | 1 | 2 | 3 | 4 | 5 | 6 |" in out
    assert "| 28 | 29 | 30 |  |  |  |  |" in out
    rows = md.markdown_table_to_rows(out)[1]
    days = [cell for row in rows for cell in row if cell]
    assert days == [str(day) for day in range(1, 31)]


def test_calendar_first_weekday_and_title() -> None:
    out = md.calendar_to_markdown(2026, 2, firstweekday=6, title="Feb")
    assert out.startswith("## Feb\n\n| Sun | Mon |")
    assert "| 1 | 2 | 3 | 4 | 5 | 6 | 7 |" in out


@pytest.mark.parametrize("kwargs", [{"month": 13}, {"month": 0}, {"month": 1, "firstweekday": 7}])
def test_calendar_rejects_out_of_range(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        md.calendar_to_markdown(2026, **kwargs)


# --- platform ---------------------------------------------------------------

def test_platform_table_has_expected_keys_and_no_host_identity() -> None:
    import platform

    out = md.platform_to_markdown()
    headers, rows = md.markdown_table_to_rows(out)
    assert headers == ["Key", "Value"]
    keys = [row[0] for row in rows]
    assert keys[:3] == ["Python", "Implementation", "Compiler"]
    assert dict(rows)["Python"] == platform.python_version()
    node = platform.node()
    if node:
        assert node not in out


# --- email ------------------------------------------------------------------

SAMPLE_MD = "# Hi\n\nSee **this** and `code`.\n\n- a\n- b\n"


def _build(**overrides: object) -> str:
    kwargs: dict = {
        "subject": "Report 日本語",
        "sender": "a@example.com",
        "to": ["b@example.com", "c@example.com"],
        "date": datetime.datetime(2026, 9, 26, 12, 0, tzinfo=datetime.timezone.utc),
    }
    kwargs.update(overrides)
    return md.markdown_to_email(SAMPLE_MD, **kwargs)


def test_markdown_to_email_is_multipart_alternative() -> None:
    import email
    from email import policy

    message = email.message_from_string(_build(), policy=policy.default)
    assert message.get_content_type() == "multipart/alternative"
    assert message["To"] == "b@example.com, c@example.com"
    assert message.get_body(("plain",)).get_content() == SAMPLE_MD
    html = message.get_body(("html",)).get_content()
    assert "<strong>this</strong>" in html


def test_email_round_trip_recovers_markdown_body_and_headers() -> None:
    out = md.email_to_markdown(_build())
    assert out.startswith("# Report 日本語\n")
    assert "| From | a@example.com |" in out
    assert "| Date | Sat, 26 Sep 2026 12:00:00 +0000 |" in out
    assert SAMPLE_MD.strip("\n") in out


def test_markdown_to_email_omits_date_when_not_given() -> None:
    assert "Date:" not in _build(date=None)


def test_markdown_to_email_rejects_header_injection() -> None:
    with pytest.raises(ValueError):
        _build(subject="hi\nBcc: victim@example.com")


def test_email_html_only_body_goes_through_html_to_markdown() -> None:
    raw = (
        "From: a@example.com\n"
        "Subject: html\n"
        "Content-Type: text/html; charset=utf-8\n"
        "\n"
        "<p>Hello <b>World</b></p><script>alert(1)</script>\n"
    )
    out = md.email_to_markdown(raw)
    assert "**World**" in out
    assert "<script>" not in out


def test_email_attachments_are_listed_not_decoded_to_disk(tmp_path: Path) -> None:
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = "files"
    msg["From"] = "a@example.com"
    msg.set_content("body text\n")
    msg.add_attachment(b"\x00\x01\x02", maintype="application", subtype="octet-stream", filename="blob.bin")
    out = md.email_to_markdown(msg.as_bytes())
    assert "## Attachments" in out
    assert "| blob.bin | application/octet-stream | 3 |" in out
    assert "body text" in out
    assert list(tmp_path.iterdir()) == []


def test_email_without_subject() -> None:
    assert md.email_to_markdown("From: a@example.com\n\nbody\n").startswith("# (no subject)\n")


# --- man --------------------------------------------------------------------

MAN_SOURCE = (
    "# Name\n\n"
    "mytool - does things\n\n"
    "## Options\n\n"
    "- `--verbose` : be **loud**\n"
    "- `-q` quiet\n\n"
    ".dangerous line\n"
    "'also dangerous\n\n"
    "```sh\n"
    "mytool --help\n"
    ".also-code\n"
    "```\n\n"
    "> quoted *text*\n\n"
    "See [docs](https://example.com) and <https://x.y>.\n"
)


def test_markdown_to_man_structure() -> None:
    out = md.markdown_to_man(MAN_SOURCE, name="mytool", date="2026-09-26")
    lines = out.splitlines()
    assert lines[0] == '.TH "MYTOOL" "1" "2026\\-09\\-26" "" ""'
    assert ".SH NAME" in lines
    assert ".SS Options" in lines
    assert "mytool \\- does things" in lines
    assert "\\fB\\-\\-verbose\\fR : be \\fBloud\\fR" in lines
    assert lines.count(".IP \\(bu 4") == 2
    assert ".EX" in lines and ".EE" in lines
    assert "quoted \\fItext\\fR" in lines
    assert "See docs <https://example.com> and https://x.y." in lines


def test_markdown_to_man_never_emits_injected_requests() -> None:
    out = md.markdown_to_man(MAN_SOURCE, name="mytool")
    known = (".TH", ".SH", ".SS", ".PP", ".IP", ".EX", ".EE", ".RS", ".RE")
    for line in out.splitlines():
        if line.startswith((".", "'")):
            assert line.startswith(known), line
    assert "\\&.dangerous line" in out
    assert "\\&'also dangerous" in out
    assert "\\&.also\\-code" in out


def test_markdown_to_man_escapes_backslashes_and_nested_lists() -> None:
    out = md.markdown_to_man("C:\\path\n\n1. one\n   - nested\n", name="x")
    assert "C:\\epath" in out
    assert ".IP \\(en 4" in out
    assert ".IP \\(bu 6" in out
