# src/candidate.py
import re
import logging
from typing import List, Optional, Tuple
from src.models import CandidateResult, Contest, EventData, Precinct

log = logging.getLogger(__name__)


class CandidateParser:
    """
    Parses candidate lines from a contest block.
    Handles:
      - Name + party (from line or event fallback)
      - Multiple vote channels: Total, Early, Absentee, Election Day
      - Skips summary rows (Cast/Over/Under Votes)
    """

    # --------------------------------------------------------------------- #
    # Regex patterns
    # --------------------------------------------------------------------- #
    _VOTE_PERCENT_PAIR = re.compile(r"(\d{1,3}(?:,\d{3})*)\s+(\d+\.\d{2})%")
    _SUMMARY_ROW = re.compile(r"^(Cast|Over|Under)\s+Votes:", re.IGNORECASE)
    _INFO_PARTY = re.compile(r"^(.*?)\s+(?:.\s+)?([A-Z]{3,}|[A-Z]+ Party)\b\.?$", re.IGNORECASE)
    _INFO_CAPTURE = re.compile(
        r"^(?!.*\bCast Votes:)(.+?)\s+(?=\d{1,3}(?:,\d{3})*\s+\d+\.\d{2}%)"
    )

    # --------------------------------------------------------------------- #
    # Public API: Parse entire block
    # --------------------------------------------------------------------- #
    @staticmethod
    def parse_block(
        lines: List[str],
        contest: Contest,
        event_party: Optional[str] = None
    ) -> List[CandidateResult]:
        """
        Parse all candidate lines in a contest block.

        Args:
            lines: List of raw lines (after contest title)
            contest: Parent Contest object (for over/undervotes)
            event_party: Fallback party from Event (e.g., "DEM" from filename)

        Returns:
            List of CandidateResult objects
        """
        candidates: List[CandidateResult] = []
        fallback_party = event_party or ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip summary rows
            if CandidateParser._SUMMARY_ROW.match(line):
                CandidateParser._capture_summary(line, contest)
                continue

            candidate = CandidateParser._parse_line(line, fallback_party)
            if candidate:
                candidate.contest = contest
                candidates.append(candidate)

        return candidates

    # --------------------------------------------------------------------- #
    # Internal: Parse one line
    # --------------------------------------------------------------------- #
    @staticmethod
    def _parse_line(line: str, fallback_party: str) -> Optional[CandidateResult]:
        info_match = CandidateParser._INFO_CAPTURE.match(line)
        if not info_match:
            return None

        candidate_info = info_match.group(1).strip()
        rest = line[info_match.end():]

        # Extract party from name
        if party_match := CandidateParser._INFO_PARTY.match(candidate_info):
            name = party_match.group(1).strip()
            party = party_match.group(2).upper()
        else:
            name = candidate_info
            party = fallback_party
            if not party:
                log.debug(f"No party for candidate: {name}")

        # Extract vote/percent pairs
        results = []
        for vote_str, _ in CandidateParser._VOTE_PERCENT_PAIR.findall(rest):
            try:
                vote_count = int(vote_str.replace(",", ""))
                results.append(vote_count)
            except ValueError:
                log.warning(f"Invalid vote count: '{vote_str}' in line: {line[:80]}")

        if not results:
            return None

        # Map to channels (in order)
        total = str(results[0])
        early = str(results[1]) if len(results) > 1 else ""
        absentee = str(results[2]) if len(results) > 2 else ""
        election_day = str(results[3]) if len(results) > 3 else ""

        return CandidateResult(
            name=name,
            party=party,
            total_votes=total,
            early_votes=early,
            absentee_votes=absentee,
            election_day_votes=election_day,
        )

    # --------------------------------------------------------------------- #
    # Internal: Capture Over/Under Votes into Contest
    # --------------------------------------------------------------------- #
    @staticmethod
    def _capture_summary(line: str, contest: Contest) -> None:
        if "Over Votes" in line:
            match = re.search(r"(\d{1,3}(?:,\d{3})*)", line)
            if match:
                contest.overvotes = match.group(1).replace(",", "")
        elif "Under Votes" in line:
            match = re.search(r"(\d{1,3}(?:,\d{3})*)", line)
            if match:
                contest.undervotes = match.group(1).replace(",", "")

    # --------------------------------------------------------------------- #
    # NEW: Build CSV rows from parsed data
    # --------------------------------------------------------------------- #
    # In src/candidate.py (inside CandidateParser class)

    