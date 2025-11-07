# src/contest.py
import re
import logging
from typing import List, Optional, Tuple

from src.models import Contest, CandidateResult
from src.config import REGULAR_EXPRESSION  # <-- make sure this exists in config.py


class ContestParser:
    """
    Parse a block of lines that belong to a single contest.
    All regexes and configuration live inside the class – no globals.
    """

    # --------------------------------------------------------------------- #
    # 1. Class-level constants (compiled once)
    # --------------------------------------------------------------------- #
    _TITLE = re.compile(
        r"^(?P<title>.+?)\s*(?:\((?:Dem|Rep|Nonpartisan|Lib|Grn|Ind|NP)\))?$",
        re.IGNORECASE,
    )

    _TOTAL_VOTES = re.compile(
        r"Cast Votes.*\s+(\d{1,3}(?:,\d{3})*)\s+\d+\.\d{2}%$"
    )

    _OVER_VOTES_1 = re.compile(
        r"Overvotes:\s+(?:\d{1,3}(?:,\d{3})*\s+)*(\d{1,3}(?:,\d{3})*)$"
    )
    _OVER_VOTES_2 = re.compile(
        r"Over Votes:\s+(?:[\d,]+\s+\d+\.\d+%\s+)*([\d,]+)\s+\d+\.\d+%$"
    )

    _UNDER_VOTES_1 = re.compile(
        r"Under Votes:\s+(?:\d{1,3}(?:,\d{3})*\s+)*(\d{1,3}(?:,\d{3})*)$"
    )
    _UNDER_VOTES_2 = re.compile(
        r"Under Votes:\s+(?:[\d,]+\s+\d+\.\d+%\s+)*([\d,]+)\s+\d+\.\d+%$"
    )

    _CANDIDATE = re.compile(
        r"""
        ^\s*
        (?P<name>.+?)                                   # Candidate name
        \s+
        \((?P<party>Dem|Rep|Lib|Grn|Ind|NP)?\)\s+       # Party (optional)
        (?P<total>\d{1,3}(?:,\d{3})*)                   # Total
        (?:\s+(?P<early>\d{1,3}(?:,\d{3})*))?           # Early (opt)
        (?:\s+(?P<absentee>\d{1,3}(?:,\d{3})*))?        # Absentee (opt)
        (?:\s+(?P<election_day>\d{1,3}(?:,\d{3})*))?    # Election Day (opt)
        \s*$
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # Optional keyword list – used only for title cleaning
    _PHRASE_MODIFIERS = [
        "Three Year Term", "Two Year Term", "Unexpired", "Incumbent"
    ]

    # --------------------------------------------------------------------- #
    # Office terms & compiled patterns (for is_contest_title)
    # --------------------------------------------------------------------- #
    OFFICE_TERMS: List[str] = [
        "City", "Proposition", "Town", "Village", "School", "Representative",
        "Governor", "General", "Public", "Municipal Utility", "Supreme",
        "Clerk", "Attorney", "Court", "Board", "Judge", "Commissioner",
        "Member", "Justice", "Lieutenant", "Comptroller", "Railroad",
        "Senator", "Criminal", "Family", "Probate", "Peace", "Library",
        "Council", "Independent", "Councilmember", "Trustee", "District",
        "Place", "Chair", "County Constable", "Assessor",
    ]

    _COMPILED_PATTERNS = [
        re.compile(rf'^(.*)\b({re.escape(term)})\b(.*)$', re.IGNORECASE)
        for term in OFFICE_TERMS
    ]

    _BLACKLIST_TITLES = [
        "Precinct Results Report",
        "Official Results",
        "Unofficial Results",
        "Summary Report",
        "Page",
        "Continued",
        "County",
        "Election",
        "Ballots Cast",
        "Registered Voters",
    ]

    _BLACKLIST_RE = re.compile(
        r"^(?:" + r"|".join(re.escape(t) for t in _BLACKLIST_TITLES) + r")",
        re.IGNORECASE,
    )

    # --------------------------------------------------------------------- #
    # 1. Is this line a contest title?
    # --------------------------------------------------------------------- #
    @staticmethod
    def is_contest_title(line: str) -> bool:
        line = line.strip()
        if not line:
            return False

        # 1. Reject black-listed report headers first
        if ContestParser._BLACKLIST_RE.match(line):
            return False

        # 2. Office-term match
        if REGULAR_EXPRESSION:
            for pattern in ContestParser._COMPILED_PATTERNS:
                if pattern.search(line):
                    return True
            return False

        # 3. Fallback "Vote for N"
        vote_for_pat = re.compile(r"\bvote for [0-9]+\b", re.IGNORECASE)
        return bool(vote_for_pat.search(line))
    
    @staticmethod
    def parse_title(line: str) -> Optional[Contest]:
        """
        Parse a single contest title line into a Contest object.
        Used by parse_pdf.py when a new title is detected.
        """
        line = line.strip()
        if not line or not ContestParser.is_contest_title(line):
            return None

        contest = Contest(title=line)

        # Extract party from (Dem), (Rep), etc.
        party_match = re.search(r"\((Dem|Rep|Nonpartisan|Lib|Grn|Ind|NP)\)", line, re.IGNORECASE)
        if party_match:
            contest.party = party_match.group(1).upper()

        # Extract modifier and vote_for
        modifier, vote_for = ContestParser._extract_title_parts(line)
        contest._modifier = modifier
        contest._vote_for = vote_for

        return contest

    # --------------------------------------------------------------------- #
    # 2. Parse full contest block
    # --------------------------------------------------------------------- #
    @staticmethod
    def parse(block: List[str]) -> Optional[Contest]:
        if not block:
            return None

        contest = Contest()
        candidates: List[CandidateResult] = []

        for raw_line in block:
            line = raw_line.strip()
            if not line:
                continue

            # ---- Title + Party -------------------------------------------------
            if not contest.title and (m := ContestParser._TITLE.match(line)):
                contest.title = m.group("title").strip()

                party_match = re.search(
                    r"\((Dem|Rep|Nonpartisan|Lib|Grn|Ind|NP)\)", line, re.IGNORECASE
                )
                if party_match:
                    contest.party = party_match.group(1).upper()

                # Extract modifier & vote-for from the raw title
                modifier, vote_for = ContestParser._extract_title_parts(contest.title)
                contest._modifier = modifier
                contest._vote_for = vote_for
                continue

            # ---- Over / Under votes -------------------------------------------
            if not contest.overvotes:
                for pat in (ContestParser._OVER_VOTES_1, ContestParser._OVER_VOTES_2):
                    if m := pat.search(line):
                        contest.overvotes = m.group(1)
                        break

            if not contest.undervotes:
                for pat in (ContestParser._UNDER_VOTES_1, ContestParser._UNDER_VOTES_2):
                    if m := pat.search(line):
                        contest.undervotes = m.group(1)
                        break

            # ---- Candidate ----------------------------------------------------
            if m := ContestParser._CANDIDATE.match(line):
                candidates.append(
                    CandidateResult(
                        name=m.group("name").strip(),
                        party=m.group("party"),
                        total_votes=m.group("total"),
                        early_votes=m.group("early") or "",
                        absentee_votes=m.group("absentee") or "",
                        election_day_votes=m.group("election_day") or "",
                    )
                )

        # ---- Finalise -------------------------------------------------------
        if contest.title:
            contest.candidates = candidates
            logging.debug(
                f"Parsed contest: {contest.title} | Vote for {contest.vote_for} | {len(candidates)} candidates"
            )
            return contest

        return None

    # --------------------------------------------------------------------- #
    # 3. Title-part extraction (replaces the old `parse_contest_name`)
    # --------------------------------------------------------------------- #
    @staticmethod
    def _extract_title_parts(raw_title: str) -> Tuple[str, str]:
        """Return (modifier, vote_for) extracted from the raw title."""
        # Vote for N
        vote_for = "1"
        if m := re.search(r"\bvote for (\d+)\b", raw_title, re.IGNORECASE):
            vote_for = m.group(1)

        # Parenthetical modifiers (skip "At large")
        paren_mods = [
            p.strip("()") for p in re.findall(r"(\((?![^)]*At large)[^)]*\))", raw_title)
        ]

        # Hyphen / comma modifiers (using the class-level list)
        hyphen_mods = []
        comma_mods = []
        if ContestParser._PHRASE_MODIFIERS:
            escaped = [re.escape(p) for p in ContestParser._PHRASE_MODIFIERS]
            phrases = "|".join(escaped)
            hyphen_pat = re.compile(rf"\s*-\s*({phrases})(?:\s|$)", re.IGNORECASE)
            comma_pat = re.compile(rf"\s*,\s*({phrases})(?:\s|$)", re.IGNORECASE)
            hyphen_mods = hyphen_pat.findall(raw_title)
            comma_mods = comma_pat.findall(raw_title)

        all_mods = paren_mods + hyphen_mods + comma_mods
        modifier = " ".join(all_mods).strip()

        return modifier, vote_for

    # --------------------------------------------------------------------- #
    # 4. Block splitter (unchanged – uses the class-level title regex)
    # --------------------------------------------------------------------- #
    @staticmethod
    def split_into_blocks(
        lines: List[str], start_idx: int = 0
    ) -> List[Tuple[int, List[str]]]:
        blocks: List[Tuple[int, List[str]]] = []
        current: List[str] = []
        idx = start_idx

        for i, line in enumerate(lines[start_idx:], start_idx):
            stripped = line.strip()
            if current and ContestParser.is_contest_title(stripped):
                blocks.append((idx, current))
                current = [line]
                idx = i
            else:
                current.append(line)

        if current:
            blocks.append((idx, current))

        return blocks