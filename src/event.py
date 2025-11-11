# src/event.py
import re
from typing import List, Optional
from src.models import EventData


class EventParser:
    """
    Parses only the **event header** (first ~15 lines of page 1).
    Returns a fully-populated EventData object.
    """

    # --------------------------------------------------------------------- #
    # Regex patterns
    # --------------------------------------------------------------------- #
    _DATE_SLASH = re.compile(
        r"^(0[1-9]|1[0-2]|[1-9])\/([1-9]|0[1-9]|[12][0-9]|3[01])\/(19|20)\d{2}$"
    )
    _DATE_MONTH = re.compile(
        r"^.*\s([A-Z]+\s[0-9][0-9],\s[0-9][0-9][0-9][0-9])$", re.IGNORECASE
    )
    _ELECTION_TYPE = re.compile(
        r"^.*\s[-—–]\s(.*election.*)\s[-—–].*", re.IGNORECASE
    )
    _COUNTY = re.compile(r"^(.*?\s*County)(.*)", re.IGNORECASE)
    _VOTERS = re.compile(r"Total Number of Voters\s*:\s+(\d{1,3}(?:,\d{3})*)")
    _BALLOTS_CAST = re.compile(r"^(\d+)\s+of\s+(\d+)\s+=\s+\d+\.\d{2}%$")
    _FILE_PARTY = re.compile(r"(Dem|Rep)", re.IGNORECASE)

    # --------------------------------------------------------------------- #
    def __init__(self, lines: List[str], filename: Optional[str] = None):
        self._lines = [l.strip() for l in lines if l.strip()]
        self.filename = filename

    # --------------------------------------------------------------------- #
    def parse(self) -> EventData:
        """Parse header and return EventData."""
        return EventData(
            date=self._extract_date(),
            election_type=self._extract_election_type(),
            county=self._extract_county(),
            total_ballots=self._extract_total_ballots(),
            party=self._extract_party(),
            precincts=[]  # will be filled by controller
        )

    # --------------------------------------------------------------------- #
    # Extraction helpers
    # --------------------------------------------------------------------- #
    def _extract_date(self) -> str:
        for line in self._lines[:10]:
            if m := self._DATE_SLASH.search(line):
                return m.group(0)
            if m := self._DATE_MONTH.search(line):
                return m.group(1)
        return ""

    def _extract_election_type(self) -> str:
        for line in self._lines[:10]:
            if m := self._ELECTION_TYPE.match(line):
                return m.group(1).strip()
        return ""

    def _extract_county(self) -> str:
        for line in self._lines[:10]:
            if m := self._COUNTY.match(line):
                return m.group(1).strip()
        return ""

    def _extract_total_ballots(self) -> str:
        for line in self._lines[:10]:
            if m := self._BALLOTS_CAST.match(line):
                return m.group(1).replace(",", "")

        for i, line in enumerate(self._lines[:10]):
            if self._VOTERS.search(line):
                try:
                    next_line = self._lines[i + 1]
                    if m := self._BALLOTS_CAST.match(next_line):
                        return m.group(1).replace(",", "")
                except IndexError:
                    pass
        return ""

    def _extract_party(self) -> str:
        if self.filename and (m := self._FILE_PARTY.search(self.filename)):
            return m.group(1).upper()
        return ""