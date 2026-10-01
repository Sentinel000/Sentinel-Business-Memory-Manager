"""Turn a WhatsApp "Export chat" file into a transcript the extractor can read.

No API, no bot, no Meta approval: the founder uses WhatsApp's own Export chat
button (group > More > Export chat > Without media) and uploads the file. The chat
never reaches Sentinel until a person chooses to share it.

What a chat gives us that a meeting recording does not: every message arrives with
its sender and its own timestamp. So "who said it" is exact rather than inferred,
and "Friday tak bhej dena" can be resolved against the day it was written rather
than the day it was uploaded.

The export format is not documented and varies by platform and phone locale:

    Android   29/09/2026, 10:04 - Ayesha Khan: Bilal, Friday tak bhej dena
    Android   9/29/26, 10:04 AM - Ayesha Khan: ...        (US locale, 12-hour)
    iPhone    [29/09/2026, 10:04:15] Ayesha Khan: ...

plus invisible direction marks, narrow no-break spaces before AM/PM, multi-line
messages, and system lines ("Ayesha added Bilal") that have no sender. Each of
those is handled explicitly below.
"""

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta

#: Generous for a text export - a busy group's year is a few megabytes. The cap is
#: there so an upload cannot exhaust memory, not to limit real use.
MAX_EXPORT_BYTES = 10 * 1024 * 1024

#: The extractor reads the whole window in one prompt; past this, the oldest
#: messages are dropped and the caller is told.
MAX_MESSAGES = 1500

# Invisible characters WhatsApp scatters through exports. Left in, they break the
# timestamp match and end up inside quoted text.
_INVISIBLE = dict.fromkeys(map(ord, "‎‏‪‫‬‭‮﻿"), None)
_SPACES = {ord(" "): " ", ord(" "): " "}

_DATE = r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})"
_TIME = r"(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp]\.?\s?[Mm]\.?)?"

_IOS = re.compile(rf"^\[{_DATE},?\s+{_TIME}\]\s+(.*)$")
_ANDROID = re.compile(rf"^{_DATE},?\s+{_TIME}\s+[-–]\s+(.*)$")

#: Messages that carry no words worth reading.
_NOISE = (
    "<media omitted>",
    "image omitted",
    "video omitted",
    "audio omitted",
    "sticker omitted",
    "gif omitted",
    "document omitted",
    "contact card omitted",
    "this message was deleted",
    "you deleted this message",
    "null",
)
_EDITED = re.compile(r"\s*<this message was edited>\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ChatMessage:
    at: datetime
    sender: str
    text: str


@dataclass(frozen=True)
class ParsedChat:
    messages: list[ChatMessage]
    #: How many lines looked like a timestamped entry - used to tell "this is not a
    #: WhatsApp export" apart from "this export has no recent messages".
    entries_seen: int
    day_first: bool


class NotAWhatsAppExport(ValueError):
    """The file does not look like WhatsApp's Export chat output."""


def _clean(line: str) -> str:
    return line.translate(_INVISIBLE).translate(_SPACES).rstrip("\r\n")


def _match(line: str):
    return _IOS.match(line) or _ANDROID.match(line)


def _infer_day_first(pairs: list[tuple[int, int]]) -> bool:
    """Day/month order is never stated, so read it off the dates themselves.

    Any first field over 12 must be a day; any second field over 12 must be a day
    in the second position. With neither, default to day-first - the order used in
    Pakistan, the UK and most of the world outside the US.
    """
    if any(a > 12 for a, _ in pairs):
        return True
    if any(b > 12 for _, b in pairs):
        return False
    return True


def _to_datetime(groups: tuple, day_first: bool) -> datetime:
    a, b, year, hour, minute, second, meridiem = groups[:7]
    day, month = (int(a), int(b)) if day_first else (int(b), int(a))
    year = int(year)
    if year < 100:
        year += 2000
    hour = int(hour)
    if meridiem:
        pm = meridiem.strip().lower().startswith("p")
        if pm and hour != 12:
            hour += 12
        elif not pm and hour == 12:
            hour = 0
    return datetime(year, month, day, hour, int(minute), int(second or 0))


def parse_export(text: str, *, day_first: bool | None = None) -> ParsedChat:
    """Every message in the export, oldest first, with system lines removed."""
    lines = [_clean(line) for line in text.splitlines()]

    matches = [(i, m) for i, line in enumerate(lines) if (m := _match(line))]
    if not matches:
        raise NotAWhatsAppExport(
            "This does not look like a WhatsApp export. In WhatsApp, open the chat, "
            "tap More > Export chat > Without media, and upload that file."
        )

    if day_first is None:
        day_first = _infer_day_first([(int(m.group(1)), int(m.group(2))) for _, m in matches])

    # Continuation lines (a message with line breaks) belong to the entry above them.
    starts = {i: m for i, m in matches}
    raw: list[tuple[datetime, str]] = []
    for i, line in enumerate(lines):
        if i in starts:
            m = starts[i]
            try:
                at = _to_datetime(m.groups(), day_first)
            except ValueError:
                # An impossible date (e.g. month 13 under the wrong order) - treat
                # the line as text rather than failing the whole import.
                if raw:
                    raw[-1] = (raw[-1][0], raw[-1][1] + "\n" + line)
                continue
            raw.append((at, m.group(8)))
        elif raw and line.strip():
            raw[-1] = (raw[-1][0], raw[-1][1] + "\n" + line)

    messages: list[ChatMessage] = []
    for at, body in raw:
        # "Sender: text". A system line ("Ayesha added Bilal", "Messages are
        # end-to-end encrypted") has no sender separator and is not a message.
        sender, sep, content = body.partition(": ")
        if not sep or not sender.strip():
            continue
        content = _EDITED.sub("", content).strip()
        if not content or content.lower() in _NOISE:
            continue
        messages.append(ChatMessage(at=at, sender=sender.strip(), text=content))

    return ParsedChat(messages=messages, entries_seen=len(matches), day_first=day_first)


def recent(messages: list[ChatMessage], days: int) -> list[ChatMessage]:
    """The last ``days`` of the conversation, measured back from its newest message.

    Measured from the chat, not from today: an export made on Tuesday of last
    week's planning should still produce last week's commitments.
    """
    if not messages:
        return []
    newest = max(m.at for m in messages)
    cutoff = newest - timedelta(days=days)
    return [m for m in messages if m.at >= cutoff]


def render_transcript(messages: list[ChatMessage]) -> str:
    """One line per message: ``[Tue 29 Sep 2026 10:04] Ayesha Khan: text``.

    The date leads every line so the extractor resolves "Friday" against the day it
    was said. Line breaks inside a message become spaces, so a quote the extractor
    copies is always one contiguous run of this text.
    """
    return "\n".join(
        f"[{m.at:%a} {m.at.day} {m.at:%b %Y %H:%M}] {m.sender}: {' '.join(m.text.split())}"
        for m in messages
    )


def group_name(filename: str | None) -> str | None:
    """'WhatsApp Chat with Delivery Team.txt' -> 'Delivery Team'."""
    if not filename:
        return None
    stem = re.sub(r"\.(txt|zip)$", "", filename.strip(), flags=re.IGNORECASE)
    named = re.match(r"^WhatsApp Chat (?:with |- )(.+)$", stem, flags=re.IGNORECASE)
    if named:
        return named.group(1).strip() or None
    if stem.lower() in ("_chat", "chat"):
        return None
    return stem or None


def read_export(data: bytes, filename: str | None) -> str:
    """The chat text from an uploaded .txt or the .zip iPhone produces."""
    if len(data) > MAX_EXPORT_BYTES:
        raise NotAWhatsAppExport("That file is larger than 10 MB. Export without media.")

    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members = [i for i in archive.infolist() if i.filename.lower().endswith(".txt")]
                if not members:
                    raise NotAWhatsAppExport("That zip has no chat text inside it.")
                # iPhone names it _chat.txt; otherwise take the only/first text file.
                member = next(
                    (i for i in members if i.filename.lower().endswith("_chat.txt")), members[0]
                )
                # Checked against the declared size before reading: a small zip can
                # declare a huge file, and reading it first is the whole attack.
                if member.file_size > MAX_EXPORT_BYTES:
                    raise NotAWhatsAppExport("The chat inside that zip is larger than 10 MB.")
                data = archive.read(member)
        except zipfile.BadZipFile:
            raise NotAWhatsAppExport("That zip file could not be opened.") from None

    return data.decode("utf-8-sig", errors="replace")
