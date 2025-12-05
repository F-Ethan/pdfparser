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
        "Place", "Chair", "Constable", "Assessor", "PRESIDENTIAL", 
        "ELECTORS", "Shall", "AMENDMENT", "REFERENDUM", "ballot"
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
    _PARTY_SUFFIX_RE = re.compile(
        r"\s*-\s*(Republican|Democratic|Libertarian|Green|Constitution|Nonpartisan|Independent)\s+Party\b",
        re.IGNORECASE,
    )

    @staticmethod
    def parse_title(raw_line: str, fallback_party: str = "") -> Optional[Contest]:
        """
        Parse a contest title line.

        Party priority:
        1. "- Republican Party" (or similar) in title
        2. "(REP)" style in title
        3. fallback_party from filename
        """
        line = raw_line.strip()
        if not line or not ContestParser.is_contest_title(line):
            return None

        contest = Contest(title=line)

        # -------------------------------------------------
        # 1. Party from suffix: "- Republican Party"
        # -------------------------------------------------
        if m := ContestParser._PARTY_SUFFIX_RE.search(line):          
            contest.party = m.group(1).upper()

        # -------------------------------------------------
        # 2. Party in parentheses: "(REP)"
        # -------------------------------------------------
        elif m := re.search(r"\((Dem|Rep|Lib|Grn|Con|NP|Ind)\)", line, re.IGNORECASE):
            contest.party = m.group(1).upper()


        # -------------------------------------------------
        # Vote-for & modifier
        # -------------------------------------------------
        modifier, vote_for = ContestParser._extract_title_parts(line)
        contest._modifier = modifier
        contest._vote_for = vote_for

        log.debug(
            "PARSED CONTEST: %s | Party: %s | VoteFor: %s | Modifier: %s",
            contest.title[:60], contest.party, vote_for, modifier,
        )
        return contest

    # --------------------------------------------------------------------- #
    # 3. Helper – extract modifier + “vote for N”
    # --------------------------------------------------------------------- #
    _MODIFIER_PHRASES = [
        "Unexpired Term",
        "Three Year Term",
        "Two Year Term",
        "Incumbent",
        "At Large",
    ]

    # Compile once
    _MODIFIER_RE = re.compile(
        r"\((?:" + r"|".join(re.escape(p) for p in _MODIFIER_PHRASES) + r")\)",
        re.IGNORECASE,
    )

    @staticmethod
    def _extract_title_parts(raw_title: str) -> Tuple[str, str]:
        """Return (modifier, vote_for) from the raw title string."""
        vote_for = "1"

        # 1. Vote for N
        if m := re.search(r"\bvote for (\d+)\b", raw_title, re.IGNORECASE):
            vote_for = m.group(1)

        # 2. Parenthetical modifiers (e.g. (Unexpired Term))
        paren_mods = [
            m.group(0).strip("()")
            for m in ContestParser._MODIFIER_RE.finditer(raw_title)
        ]

        # 3. Hyphen / comma modifiers
        hyphen_mods = []
        comma_mods = []
        if ContestParser._MODIFIER_PHRASES:
            escaped = [re.escape(p) for p in ContestParser._MODIFIER_PHRASES]
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
    def parse_title(raw_line: str, fallback_party: str = "") -> Optional[Contest]:
        line = raw_line.strip()
        if not line or not ContestParser.is_contest_title(line):
            return None

        # --- 1. Extract modifier & vote_for ---
        modifier, vote_for = ContestParser._extract_title_parts(line)

        # --- 2. Clean title: remove (Unexpired Term), etc. ---
        clean_title = ContestParser._MODIFIER_RE.sub("", line)
        clean_title = re.sub(r"\s*-\s*(Unexpired Term|Three Year Term|Two Year Term|Incumbent|At Large)", "", clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s*,\s*(Unexpired Term|Three Year Term|Two Year Term|Incumbent|At Large)", "", clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\s{2,}", " ", clean_title).strip(", ").strip()
        
        contest = Contest(title=clean_title, modifier=modifier)

        # --- 3. Party priority ---
        if m := ContestParser._PARTY_SUFFIX_RE.search(line):
            contest.party = m
        elif m := re.search(r"\((Dem|Rep|Lib|Grn|Con|NP|Ind)\)", line, re.IGNORECASE):
            contest.party = m.group(1).upper()
        else:
            contest.party = fallback_party.upper() if fallback_party else ""

        contest._vote_for = vote_for

        log.debug(
            "PARSED CONTEST: %s | Party: %s | VoteFor: %s | Modifier: %s",
            contest.title[:60], contest.party, vote_for, modifier,
        )
        return contest

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