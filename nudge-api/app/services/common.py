import re
import uuid
from datetime import UTC, date, datetime


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def new_id() -> str:
    return str(uuid.uuid4())


_TERM_START = {"Spring": (1, 12), "Summer": (5, 18), "Fall": (8, 24)}


def semester_start(name: str) -> date:
    """Approximate first day of a semester like 'Fall 2026'."""
    term, _, year = name.partition(" ")
    month, day = _TERM_START.get(term, (1, 1))
    return date(int(year), month, day)


def semester_sort_key(name: str) -> date:
    try:
        return semester_start(name)
    except ValueError:
        return date.min


_NUMBERED_TITLE = re.compile(
    r"^((?:lecture|lec|lab|homework|hw|problem set|ps|week|chapter|unit|quiz|exam|recitation|section)\s*\d+)\b",
    re.IGNORECASE,
)


# iOS adds the photo's ID to picked file names: "IMG_0042-70B62FA5-76AA-41FD-B35E-BB958B925F72"
_PHOTO_ID = re.compile(r"-[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$", re.IGNORECASE)
_SCREENSHOT = re.compile(r"^Screen ?shot \d{4}-(\d{2})-(\d{2})\b", re.IGNORECASE)
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def citation_title(material_title: str) -> str:
    """Short name for citation chips.

    'Lecture 6 - Substitution.pdf' -> 'Lecture 6'
    'lecture-7-integration-by-parts.pdf' -> 'Lecture 7'
    'Problem_Set_4.pdf' -> 'Problem Set 4', 'Syllabus.pdf' -> 'Syllabus'
    'Screenshot 2026-10-29 at 12.25.36 AM-70B62FA5-....png' -> 'Screenshot Oct 29'
    """
    title = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", material_title).strip()
    title = _PHOTO_ID.sub("", title)
    screenshot = _SCREENSHOT.match(title)
    if screenshot:
        return f"Screenshot {MONTHS[int(screenshot.group(1)) - 1]} {int(screenshot.group(2))}"
    if " " not in title:
        title = re.sub(r"[-_]+", " ", title)
    title = title.split(" - ")[0].strip()
    numbered = _NUMBERED_TITLE.match(title)
    if numbered:
        title = numbered.group(1)
    title = re.sub(r"\s+", " ", title)
    return title[:1].upper() + title[1:]
