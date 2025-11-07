import re
from src.models import EventData, Precinct, Contest
from src.precinct import PrecinctParser
from src.contest import ContestParser
from typing import List, Tuple, Optional



class EventParser:
    """Parse the first ~10 lines of a PDF page and expose structured event data."""

    # --------------------------------------------------------------------- #
    # Regex patterns 
    # --------------------------------------------------------------------- #
    _FILE_PARTY = re.compile(r"(Dem|Rep)", re.IGNORECASE)
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

    _VOTERS = re.compile(
        r"Total Number of Voters\s*:\s+(\d{1,3}(?:,\d{3})*)"
    )
    _BALLOTS_CAST = re.compile(r"^(\d+)\s+of\s+(\d+)\s+=\s+\d+\.\d{2}%$")


    # --------------------------------------------------------------------- #

    def __init__(self, lines: List[str]):
        self._lines = [l.strip() for l in lines if l.strip()]   # clean copy
        self._precincts: List[Precinct] = []

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    @property
    def data(self) -> EventData:
        """Return the parsed event data (lazy – computed once per call)."""
        return EventData(
            date=self._extract_date(),
            election_type=self._extract_election_type(),
            county=self._extract_county(),
            total_ballots=self._extract_total_ballots(),
        )
    
    @property
    def precincts(self) -> List[Precinct]:
        if not self._precincts:
            self._precincts = self._extract_precincts()
        return self._precincts
    
    @property
    def contests(self) -> List[Contest]:
        """Lazily parse contests from the full page."""
        if not hasattr(self, "_contests"):
            self._contests = self._extract_contests()
        return self._contests

    def _extract_contests(self) -> List[Contest]:
        """Find contest blocks and parse them."""
        contests = []
        # Assume contests start after precincts — skip first 50 lines as safe buffer
        contest_lines = self._lines[50:]

        for _, block in ContestParser.split_into_blocks(contest_lines):
            if contest := ContestParser.parse(block):
                contests.append(contest)
        return contests


    # --------------------------------------------------------------------- #
    # Private extraction helpers
    # --------------------------------------------------------------------- #

    def _extract_precincts(self) -> List[Precinct]:
        precincts = []
        for line in self._lines[10:]:  # skip header
            if precinct := PrecinctParser.parse(line):
                precincts.append(precinct)
        return precincts
    
    def _extract_date(self) -> str:
        for line in self._lines[:10]:
            if m := self._DATE_SLASH.match(line):
                return m.group(0)
            if m := self._DATE_MONTH.match(line):
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
        # 1. Direct “Number of Voters” line (placeholder pattern)
        for line in self._lines[:10]:
            if m := self._BALLOTS_CAST.match(line):
                return m.group(1)

        # 2. Fallback: line after “Registered Voters”
        for i, line in enumerate(self._lines[:10]):
            if self._VOTERS.search(line):
                try:
                    next_line = self._lines[i + 1]
                    if m := self._BALLOTS_CAST.match(next_line):
                        return m.group(1)
                except IndexError:
                    pass
        return ""

    # --------------------------------------------------------------------- #
    # Optional: expose the party-from-filename helper
    # --------------------------------------------------------------------- #
    @staticmethod
    def party_from_filename(filename: str) -> str:
        """Utility used when PARTY_BY_FILE=True."""
        if m := Event._FILE_PARTY.search(filename):
            return m.group(1).upper()
        return ""