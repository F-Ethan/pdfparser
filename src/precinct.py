# src/precinct.py
import re
from typing import Optional
from src.models import Precinct
import logging

class PrecinctParser:
    """
    Static parser: takes a line → returns a Precinct object or None.
    No state. No __init__. Reusable. Testable.
    """

    # --------------------------------------------------------------------- #
    # Regex Patterns (compiled once)
    # --------------------------------------------------------------------- #
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
            PrecinctParser._parse_simple,
            PrecinctParser._parse_parenthetical,
            PrecinctParser._parse_with_registered,
        ]

        for parser in parsers:
            if result := parser(line):
                logging.debug(f"Parsed precinct: {result.number} → {result.ballots_cast}")
                return result

        logging.debug(f"No precinct match: '{line}'")
        return None

    # --------------------------------------------------------------------- #
    # Private parsers
    # --------------------------------------------------------------------- #
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