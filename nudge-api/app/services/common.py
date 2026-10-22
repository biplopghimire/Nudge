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


def citation_title(material_title: str) -> str:
    """'Lecture 6 - Substitution.pdf' -> 'Lecture 6'."""
    title = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", material_title)
    return title.split(" - ")[0].strip()
