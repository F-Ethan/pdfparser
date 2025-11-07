# src/candidate.py
import re
import logging
from typing import List, Tuple, Optional
from src.models import CandidateResult


class CandidateParser:
    """
    Parses a single candidate line → CandidateResult object.
    Handles:
      - Name + party (from line or filename fallback)
      - Multiple vote/percent pairs (by channel)
      - Skips summary rows (Cast/Over/Under Votes)
    """

    # --------------------------------------------------------------------- #
    # Regexes (class-level, compiled once)
    # --------------------------------------------------------------------- #
    _VOTE_PERCENT_PAIR = re.compile(r"(\d{1,3}(?:,\d{3})*)\s+(\d+\.\d{2})%")
    _SUMMARY_ROW = re.compile(r"^(Cast|Over|Under)\s+Votes:", re.IGNORECASE)
    _INFO_PARTY = re.compile(r"^(.*)\s+([A-Z]{3,})\b\.?$", re.IGNORECASE)
    _INFO_CAPTURE = re.compile(
        r"^(?!.*\bCast Votes:)(.+?)\s+(?=\d{1,3}(?:,\d{3})*\s+\d+\.\d{2}%)"
    )

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    @staticmethod
    def parse(
        line: str,
        file_party: Optional[str] = None
    ) -> Optional[CandidateResult]:
        """
        Parse one candidate line.

        Args:
            line: Raw line from PDF
            file_party: Fallback party if not in line and PARTY_BY_FILE is used

        Returns:
            CandidateResult or None if not a candidate line
        """
        line = line.strip()
        if not line:
            return None

        # 1. Skip summary rows
        if CandidateParser._SUMMARY_ROW.match(line):
            logging.debug(f"Skipping summary line: {line[:60]}...")
            return None

        # 2. Extract name/party info before first vote/percent
        info_match = CandidateParser._INFO_CAPTURE.match(line)
        if not info_match:
            return None

        candidate_info = info_match.group(1).strip()
        rest = line[info_match.end():]

        # 3. Extract party from name
        if party_match := CandidateParser._INFO_PARTY.match(candidate_info):
            name = party_match.group(1).strip()
            party = party_match.group(2).upper()
        else:
            name = candidate_info
            party = file_party or ""
            if not party:
                logging.warning(f"No party found for candidate: {name}")

        # 4. Extract vote/percent pairs
        results: List[Tuple[int, float]] = []
        for vote_str, pct_str in CandidateParser._VOTE_PERCENT_PAIR.findall(rest):
            try:
                vote_count = int(vote_str.replace(",", ""))
                percent = float(pct_str)
                results.append((vote_count, percent))
            except ValueError:
                logging.warning(f"Invalid vote/percent: '{vote_str}' / '{pct_str}'")

        # 5. Map to vote channels (in order: Total, Early, Absentee, Election Day)
        if not results:
            return None

        total_votes = str(results[0][0])
        early = str(results[1][0]) if len(results) > 1 else ""
        absentee = str(results[2][0]) if len(results) > 2 else ""
        election_day = str(results[3][0]) if len(results) > 3 else ""

        return CandidateResult(
            name=name,
            party=party,
            total_votes=total_votes,
            early_votes=early,
            absentee_votes=absentee,
            election_day_votes=election_day,
        )