# src/candidate.py
import re
import logging
from typing import List, Optional
from src.models import CandidateResult, Contest

log = logging.getLogger(__name__)


class CandidateParser:
    """One-line candidate parser – no parentheses required for party."""

    # --------------------------------------------------------------------- #
    # 1. Summary lines (Cast / Over / Under)
    # --------------------------------------------------------------------- #
    _SUMMARY = re.compile(r"^(Cast|Over|Under)\s*[Vv]otes?:?", re.IGNORECASE)

    # --------------------------------------------------------------------- #
    # 2. Vote-count + optional % (e.g. "12 60.00%" or just "12")
    # --------------------------------------------------------------------- #
    _VOTE = re.compile(r"(\d{1,3}(?:,\d{3})*)\s*(?:\d+\.\d{2}%)?")

    # --------------------------------------------------------------------- #
    # 3. Party – any 3-letter code that is NOT part of the name
    # --------------------------------------------------------------------- #
    _PARTY = re.compile(r"\b(Dem|Rep|Gre|Grn|Lib|Ind|NP|Nonpartisan)\b", re.IGNORECASE)

    # --------------------------------------------------------------------- #
    @staticmethod
    def parse_block(
        lines: List[str],
        contest: Contest,
        event_party: Optional[str] = None,
    ) -> List[CandidateResult]:
        candidates: List[CandidateResult] = []
        fallback = event_party or ""

        for raw in lines:
            line = raw.strip()
            if not line:
                continue

            # ----- summary rows -----
            if CandidateParser._SUMMARY.match(line):
                CandidateParser._capture_summary(line, contest)
                continue

            # ----- candidate row -----
            cand = CandidateParser._parse_line(line, fallback)
            if cand:
                cand.contest = contest
                candidates.append(cand)
            else:
                log.debug("SKIP candidate line (no match): %s", line[:80])

        return candidates

    # --------------------------------------------------------------------- #
    @staticmethod
    def _parse_line(line: str, fallback_party: str) -> Optional[CandidateResult]:
        # 1. Find ALL vote counts first
        votes = CandidateParser._VOTE.findall(line)
        if not votes:
            log.debug("No vote numbers → reject: %s", line[:80])
            return None

        # 2. Remove vote/percent pairs from the line → left with name + possible party
        name_and_party = CandidateParser._VOTE.sub("", line)
        name_and_party = re.sub(r"\s+", " ", name_and_party).strip()

        # 3. Look for a party code (Dem, Rep, etc.)
        party = None
        party_match = CandidateParser._PARTY.search(name_and_party)
        if party_match:
            party = party_match.group(1).upper()
            name_and_party = CandidateParser._PARTY.sub("", name_and_party)

        # 4. Whatever is left is the name
        name = name_and_party.strip()
        if not name:
            log.debug("Empty name after cleaning: %s", line[:80])
            return None

        # 5. Map the 4 possible channels (Total is always the **last** number)
        total = votes[-1].replace(",", "")
        absentee = votes[0].replace(",", "") if len(votes) > 2 else ""
        early = votes[1].replace(",", "") if len(votes) > 1 else ""
        election_day = votes[2].replace(",", "") if len(votes) > 3 else ""

        result = CandidateResult(
            name=name,
            party=party or fallback_party,
            total_votes=total,        
            early_votes=early,
            absentee_votes=absentee,
            election_day_votes=election_day,
        )
        

        log.debug(
            "CANDIDATE → %s | Party:%s | T:%s E:%s A:%s D:%s",
            name, result.party, total, early, absentee, election_day,
        )
        return result
    
    @staticmethod
    def _capture_summary(line: str, contest: Contest) -> None:
        line = line.strip()
        total = None

        # -------------------------------------------------
        # 1. Format WITH percentages (common in Cast Votes)
        # -------------------------------------------------
        if m := re.search(r"(?:Cast|Over|Under)\s*[Vv]otes?[:\s]+.*?\s+(\d{1,3}(?:,\d{3})*)\s+\d+\.\d{2}%$", line):
            total = m.group(1).replace(",", "")

        # -------------------------------------------------
        # 2. Format WITHOUT percentages (common in Over/Under)
        # -------------------------------------------------
        elif m := re.search(r"(?:Cast|Over|Under)\s*[Vv]otes?[:\s]+.*?\s+(\d{1,3}(?:,\d{3})*)$", line):
            total = m.group(1).replace(",", "")

        # -------------------------------------------------
        # 3. Fallback: last number in the line (for "undervotes 2 45 65 112")
        # -------------------------------------------------
        elif m := re.search(r"(?:Cast|Over|Under)\s*[Vv]otes?[:\s]+.*?\s+(\d{1,3}(?:,\d{3})*)\s*", line):
            # Find ALL numbers, take the last one
            votes = re.findall(r"\d{1,3}(?:,\d{3})*", line)
            if votes:
                total = votes[-1].replace(",", "")

        if not total:
            return

        # Assign to correct field
        if re.search(r"Over\s*[Vv]otes?", line, re.IGNORECASE):
            contest.overvotes = total
        elif re.search(r"Under\s*[Vv]otes?", line, re.IGNORECASE):
            contest.undervotes = total
        elif re.search(r"Cast\s*[Vv]otes?", line, re.IGNORECASE):
            contest.cast_votes = total