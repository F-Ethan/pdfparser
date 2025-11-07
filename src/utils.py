# src/utils.py
import re
from typing import List, Dict
from collections import defaultdict

# --------------------------------------------------------------------- #
# Regex patterns (compile once)
# --------------------------------------------------------------------- #
FILE_PARTY_PATTERN = re.compile(r"(Dem|Rep)", re.IGNORECASE)

DATE_MMDDYYYY = re.compile(
    r"^(0[1-9]|1[0-2]|[1-9])\/([1-9]|0[1-9]|[12][0-9]|3[01])\/(19|20)\d{2}$"
)
DATE_MONTH = re.compile(
    r"^.*\s([A-Z][a-z]+\s+\d{1,2},\s+\d{4})$", re.IGNORECASE
)
ELECTION_TYPE = re.compile(
    r"^.*\s[-—–]\s(.*election.*)\s[-—–].*", re.IGNORECASE
)
COUNTY_PATTERN = re.compile(r"^(.*?\s*County)(.*)", re.IGNORECASE)
TOTAL_VOTERS = re.compile(r"Total Number of Voters\s*:\s+(\d{1,3}(?:,\d{3})*)")

# Precinct patterns
PRECINCT_PATTERNS = [
    re.compile(r"^(\d{1,3}(?:,\d{3})*|\d+\s+-\s+\d{1,3}(?:,\d{3})*|\d+)\s+(\d{1,3}(?:,\d{3})*|\d+)\s+ballots cast"),
    re.compile(r'''
        ^(?:Precinct\s*)?
        (\d+(?:\s*-\s*\d+)?(?:,\d{3})*)\s*
        (?:\(Ballots\s+Cast:\s*(\d{1,3}(?:,\d{3})*)\)\s*$|\s+(\d{1,3}(?:,\d{3})*)\s+ballots\s+cast)
    ''', re.IGNORECASE | re.VERBOSE),
    re.compile(r"^(\d+)\s+(\d{1,3}(?:,\d{3})*)\s+of\s+(\d{1,3}(?:,\d{3})*)\s+registered voters"),
]

# Vote summary
TOTAL_VOTES_PATTERN = re.compile(r"Cast Votes.*\s+(\d{1,3}(?:,\d{3})*)")
OVERVOTES_PATTERN = re.compile(r"Overvotes:\s+(?:\d{1,3}(?:,\d{3})*\s+)*(\d{1,3}(?:,\d{3})*)")
UNDERVOTES_PATTERN = re.compile(r"Under Votes:\s+(?:\d{1,3}(?:,\d{3})*\s+)*(\d{1,3}(?:,\d{3})*)")

# Candidate vote pairs
VOTE_PERCENT_PAIR = re.compile(r"(\d{1,3}(?:,\d{3})*)\s+(\d+\.\d{2})%")

# Office terms
OFFICE_TERMS = [
    "City", "Proposition", "Town", "Village", "School", "Representative",
    "Governor", "General", "Public", "Municipal Utility", "Supreme",
    "Clerk", "Attorney", "Court", "Board", "Judge", "Commissioner",
    "Member", "Justice", "Lieutenant", "Comptroller", "Railroad",
    "Senator", "Criminal", "Family", "Probate", "Peace", "Library",
    "Council", "Independent", "Councilmember", "Trustee", "District",
    "Place", "Chair", "County Constable", "Assessor",
]
OFFICE_PATTERNS = [re.compile(rf'^(.*)\b({re.escape(term)})\b(.*)$', re.IGNORECASE) for term in OFFICE_TERMS]

# --------------------------------------------------------------------- #
# Helper: group words into lines
# --------------------------------------------------------------------- #
def group_words_into_lines(words: List[dict]) -> List[str]:
    if not words:
        return []
    lines: defaultdict[float, List[dict]] = defaultdict(list)
    for w in words:
        y = round(w["top"], 1)
        lines[y].append(w)
    result = []
    for y in sorted(lines.keys()):
        sorted_words = sorted(lines[y], key=lambda w: w["x0"])
        line_text = " ".join(w["text"] for w in sorted_words if w["text"].strip())
        if line_text := line_text.strip():
            result.append(line_text)
    return result