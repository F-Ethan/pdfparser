# src/precinct.py
import re
from typing import Optional
from src.models import Precinct
from src.logger import get_logger
log = get_logger(__name__)      # or just get_logger()

class PrecinctParser:
    """
    Static parser: takes a line → returns a Precinct object or None.
    No state. No __init__. Reusable. Testable.
    """

    # --------------------------------------------------------------------- #
    # Regex Patterns (compiled once)
    # --------------------------------------------------------------------- #

    # --------------------------------------------------------------------- #
    # ONE REGEX – three capture groups (only the ones that exist are filled)
    # --------------------------------------------------------------------- #
    # 1.  "1 113 of 0 registered voters = 0.00%"
    # 2.  "Precinct1001-001 (Ballots Cast:286)"
    # 3.  "1001 379 of 1,760 registered voters = 21.53%"
    #
    #   (?P<num>…)          → precinct number (may contain a dash + letter)
    #   (?P<cast>…)         → ballots cast
    #   (?P<reg>…)          → registered voters (optional)
    #   (?P<paren_cast>…)   → ballots cast inside parentheses (optional)
    #
    _ROBUST = re.compile(
        r"""
        ^\s*                                   # leading whitespace
        (?:Precinct\s*)?                       # optional "Precinct"
        (?P<num>\d+(?:-\w+)?)                  # precinct number
        \s+
        (?:                                    # ----- two possible ways to report cast -----
            # 1.  "113 ballots cast"
            (?P<cast>\d{1,3}(?:,\d{3})*)\s+ballots\s+cast
            |
            # 2.  "(Ballots Cast:286)"
            \(\s*Ballots\s+Cast:\s*(?P<paren_cast>\d{1,3}(?:,\d{3})*)\s*\)
        )
        (?:\s+of\s+(?P<reg>\d{1,3}(?:,\d{3})*)\s+registered\s+voters)?   # optional registered
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _SIMPLE = re.compile(
        r"^\s*(?:Precinct\s*)?(\d+(?:-\w+)?)\s+(\d{1,3}(?:,\d{3})*)\s+ballots\s+cast",
        re.IGNORECASE
    )
    # → "123 456 ballots cast" or "Precinct 1-AB 1,234 ballots cast"

    _PARENTHETICAL = re.compile(
        r"^\s*(?:Precinct\s*)?(\d+(?:-\w+)?)\s*\(Ballots Cast:\s*(\d{1,3}(?:,\d{3})*)\)",
        re.IGNORECASE
    )
    # → "123 (Ballots Cast: 456)"

    _WITH_REGISTERED = re.compile(
        r"^\s*(\d+(?:-\w+)?)\s+(\d{1,3}(?:,\d{3})*)\s+of\s+(\d{1,3}(?:,\d{3})*)\s+registered voters",
        re.IGNORECASE
    )
    # → "1-AB 456 of 1,234 registered voters = 98.76%"

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    @staticmethod
    def parse(line: str) -> Optional[Precinct]:
        """
        Try all patterns. Return first match as Precinct object.
        Return None if no match.
        """
        line = line.strip()
        if not line:
            return None

        parsers = [
            PrecinctParser._parse_robust,
            PrecinctParser._parse_simple,
            PrecinctParser._parse_parenthetical,
            PrecinctParser._parse_with_registered,
        ]

        for parser in parsers:
            if result := parser(line):
                log.debug(f"Parsed precinct: {result.number} → {result.ballots_cast}")
                return result

        log.debug(f"No precinct match: '{line}'")
        return None

    # --------------------------------------------------------------------- #
    # Private parsers
    # --------------------------------------------------------------------- #
    @staticmethod
    def _parse_robust(line: str) -> Optional[Precinct]:
        m = PrecinctParser._ROBUST.match(line)
        if not m:
            return None

        num   = m.group("num")
        cast  = (m.group("cast") or m.group("paren_cast") or "").replace(",", "")
        reg   = (m.group("reg") or "").replace(",", "")

        precinct = Precinct(
            number=num,            # you can enrich later
            ballots_cast=cast,
            registered_voters=reg,
        )
        return precinct



    
    @staticmethod
    def _parse_simple(line: str) -> Optional[Precinct]:
        if m := PrecinctParser._SIMPLE.match(line):
            return Precinct(number=m.group(1), ballots_cast=m.group(2))
        return None

    @staticmethod
    def _parse_parenthetical(line: str) -> Optional[Precinct]:
        if m := PrecinctParser._PARENTHETICAL.match(line):
            return Precinct(number=m.group(1), ballots_cast=m.group(2))
        return None

    @staticmethod
    def _parse_with_registered(line: str) -> Optional[Precinct]:
        if m := PrecinctParser._WITH_REGISTERED.match(line):
            return Precinct(
                number=m.group(1),
                ballots_cast=m.group(2),
                registered_voters=m.group(3)  # optional field
            )
        return None