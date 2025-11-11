# src/contest.py
import re
import logging
from typing import List, Optional, Tuple

from src.models import Contest, CandidateResult
from src.config import REGULAR_EXPRESSION  # set to True/False in config.py

log = logging.getLogger(__name__)


class ContestParser:
    """
    All contest-related parsing lives here.
    No class-level mutable state – everything is pure functions.
    """

    # --------------------------------------------------------------------- #
    # 1. Title detection (used by the controller)
    # --------------------------------------------------------------------- #
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


    @staticmethod
    def is_contest_title(line: str) -> bool:
        """Return True if the line looks like a contest title."""
        line = line.strip()
        if not line:
            return False

        # -------------------------------------------------
        # 1. BLACKLIST – never treat these as contest titles
        # -------------------------------------------------
        if ContestParser._BLACKLIST_RE.match(line):
            return False

        # NEW: Block any line that starts with "Precinct"
        if line.lower().startswith("precinct"):
            log.debug(f"BLACKLISTED (Precinct): {line[:60]}")
            return False

        # NEW: Block page footers like "Page9of500 05/14/2019"
        if re.match(r"^Page\d+of\d+", line, re.IGNORECASE):
            return False

        # -------------------------------------------------
        # 2. REGULAR EXPRESSION MODE (your config)
        # -------------------------------------------------
        if REGULAR_EXPRESSION:
            return any(p.search(line) for p in ContestParser._COMPILED_PATTERNS)

        # -------------------------------------------------
        # 3. FALLBACK: “Vote for N”
        # -------------------------------------------------
        return bool(re.search(r"\bvote for \d+\b", line, re.IGNORECASE))

    # --------------------------------------------------------------------- #
    # 2. Parse a **single** title line → Contest object
    # --------------------------------------------------------------------- #
    @staticmethod
    def parse_title(raw_line: str) -> Optional[Contest]:
        """
        Called by the controller the moment a new title is detected.
        Returns a *bare* Contest (no candidates yet).
        """
        line = raw_line.strip()
        if not line or not ContestParser.is_contest_title(line):
            return None

        contest = Contest(title=line)

        # ---- party in parentheses ------------------------------------------------
        if m := re.search(r"\((Dem|Rep|Nonpartisan|Lib|Grn|Ind|NP)\)", line, re.IGNORECASE):
            contest.party = m.group(1).upper()

        # ---- vote-for & modifier ------------------------------------------------
        modifier, vote_for = ContestParser._extract_title_parts(line)
        contest._modifier = modifier
        contest._vote_for = vote_for

        return contest

    # --------------------------------------------------------------------- #
    # 3. Helper – extract modifier + “vote for N”
    # --------------------------------------------------------------------- #
    _PHRASE_MODIFIERS = [
        "Three Year Term", "Two Year Term", "Unexpired", "Incumbent"
    ]

    @staticmethod
    def _extract_title_parts(raw_title: str) -> Tuple[str, str]:
        """Return (modifier, vote_for) from the raw title string."""
        # default
        vote_for = "1"

        # Vote for N
        if m := re.search(r"\bvote for (\d+)\b", raw_title, re.IGNORECASE):
            vote_for = m.group(1)

        # Parenthetical modifiers (skip “At large”)
        paren_mods = [
            p.strip("()")
            for p in re.findall(r"(\((?![^)]*At large)[^)]*\))", raw_title)
        ]

        # Hyphen / comma modifiers from the class list
        hyphen_mods = []
        comma_mods = []
        if ContestParser._PHRASE_MODIFIERS:
            escaped = [re.escape(p) for p in ContestParser._PHRASE_MODIFIERS]
            phrases = "|".join(escaped)
            hyphen_pat = re.compile(rf"\s*-\s*({phrases})(?:\s|$)", re.IGNORECASE)
            comma_pat  = re.compile(rf"\s*,\s*({phrases})(?:\s|$)", re.IGNORECASE)
            hyphen_mods = hyphen_pat.findall(raw_title)
            comma_mods  = comma_pat.findall(raw_title)

        modifier = " ".join(paren_mods + hyphen_mods + comma_mods).strip()
        return modifier, vote_for

    # --------------------------------------------------------------------- #
    # 4. **Optional** – full block parser (kept for legacy code or tests)
    # --------------------------------------------------------------------- #
    _OVER_VOTES_1 = re.compile(r"Overvotes:\s+(?:\d{1,3}(?:,\d{3})*\s+)*(\d{1,3}(?:,\d{3})*)")
    _OVER_VOTES_2 = re.compile(r"Over Votes:\s+(?:[\d,]+\s+\d+\.\d+%\s+)*([\d,]+)\s+\d+\.\d+%")
    _UNDER_VOTES_1 = re.compile(r"Under Votes:\s+(?:\d{1,3}(?:,\d{3})*\s+)*(\d{1,3}(?:,\d{3})*)")
    _UNDER_VOTES_2 = re.compile(r"Under Votes:\s+(?:[\d,]+\s+\d+\.\d+%\s+)*([\d,]+)\s+\d+\.\d+%")

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

    @staticmethod
    def parse(block: List[str]) -> Optional[Contest]:
        """
        Legacy full-block parser – returns a *complete* Contest with candidates.
        You probably won’t call this from the controller any more.
        """
        if not block:
            return None

        contest = Contest()
        candidates: List[CandidateResult] = []

        for raw_line in block:
            line = raw_line.strip()
            if not line:
                continue

            # ---- title -------------------------------------------------
            if not contest.title:
                if m := re.match(r"^(?P<title>.+?)\s*(?:\((?:Dem|Rep|Nonpartisan|Lib|Grn|Ind|NP)\))?$", line, re.IGNORECASE):
                    contest.title = m.group("title").strip()
                    if pm := re.search(r"\((Dem|Rep|Nonpartisan|Lib|Grn|Ind|NP)\)", line, re.IGNORECASE):
                        contest.party = pm.group(1).upper()
                    modifier, vote_for = ContestParser._extract_title_parts(contest.title)
                    contest._modifier = modifier
                    contest._vote_for = vote_for
                    continue

            # ---- over / under -------------------------------------------
            for pat in (ContestParser._OVER_VOTES_1, ContestParser._OVER_VOTES_2):
                if not contest.overvotes and (m := pat.search(line)):
                    contest.overvotes = m.group(1).replace(",", "")
            for pat in (ContestParser._UNDER_VOTES_1, ContestParser._UNDER_VOTES_2):
                if not contest.undervotes and (m := pat.search(line)):
                    contest.undervotes = m.group(1).replace(",", "")

            # ---- candidate ----------------------------------------------
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

        if contest.title:
            contest.candidates = candidates
            log.debug(
                f"Legacy parse: {contest.title} | Vote for {contest.vote_for} | {len(candidates)} cand."
            )
            return contest
        return None

    # --------------------------------------------------------------------- #
    # 5. Block splitter – useful for debugging / unit-tests
    # --------------------------------------------------------------------- #
    @staticmethod
    def split_into_blocks(lines: List[str], start_idx: int = 0) -> List[Tuple[int, List[str]]]:
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