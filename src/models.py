# src/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import re


# --------------------------------------------------------------------- #
# 1. Event
# --------------------------------------------------------------------- #
@dataclass
class EventData:
    date: str = ""
    election_type: str = ""
    county: str = ""
    total_ballots: str = ""
    party: str = ""

    precincts: List['Precinct'] = field(default_factory=list)

    def to_csv_rows(self) -> List[dict]:
        rows = []
        for precinct in self.precincts:
            for contest in precinct.contests:
                for cand in contest.candidates:
                    rows.append({
                        "Event Date": self.date,
                        "Event Type": self.election_type,
                        "County": self.county,
                        "Precinct Name": precinct.name,
                        "Candidate": cand.name,
                        "Total Votes Cast": cand.total_votes,
                        "Office": contest.office,
                        "# of winners": contest.vote_for,  # ← fixed
                        "Total Ballots Cast": self.total_ballots,
                        "Ballots Cast": precinct.ballots_cast,
                        "Over Votes": precinct.overvotes or "N/A",
                        "Undervotes": precinct.undervotes or "N/A",
                        "Candidate Party": cand.party or "",
                        "Contest Party": self.party,
                        "Raw Title": contest.title,
                    })
        return rows


# --------------------------------------------------------------------- #
# 2. Precinct
# --------------------------------------------------------------------- #
@dataclass
class Precinct:
    number: str
    name: str = ""
    ballots_cast: str = ""
    registered_voters: str = ""
    overvotes: str = ""
    undervotes: str = ""

    contests: List['Contest'] = field(default_factory=list)
    event: Optional[EventData] = None  # back-link


# --------------------------------------------------------------------- #
# 3. Contest
# --------------------------------------------------------------------- #
@dataclass
class Contest:
    title: str = ""
    party: Optional[str] = None
    overvotes: str = ""
    undervotes: str = ""

    precinct: Optional[Precinct] = None  # back-link
    candidates: List['CandidateResult'] = field(default_factory=list)

    _vote_for: str = "1"

    @property
    def vote_for(self) -> str:
        return self._vote_for

    @property
    def office(self) -> str:
        base = self.title.split(" - ", 1)[0]
        base = re.sub(r"\s*[\(\[]?(Vote|Elect|Choose|Top)\s+\d+[\)\]]?", "", base, flags=re.IGNORECASE)
        return base.strip()


# --------------------------------------------------------------------- #
# 4. Candidate
# --------------------------------------------------------------------- #
@dataclass
class CandidateResult:
    name: str
    party: Optional[str] = None
    total_votes: str = ""
    early_votes: str = ""
    absentee_votes: str = ""
    election_day_votes: str = ""

    contest: Optional[Contest] = None  # back-link

    @property
    def vote_channel(self) -> str:
        if self.total_votes:
            return "Total"
        if self.early_votes:
            return "Early"
        if self.absentee_votes:
            return "Absentee"
        if self.election_day_votes:
            return "Election Day"
        return "Total"