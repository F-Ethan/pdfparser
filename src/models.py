# src/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import re



# --------------------------------------------------------------------- #
# 1. Event header
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class EventData:
    date: str = ""
    election_type: str = ""
    county: str = ""
    total_ballots: str = ""


# --------------------------------------------------------------------- #
# 2. Precinct
# --------------------------------------------------------------------- #
@dataclass
class Precinct:
    number: str
    name: str = ""
    ballots_cast: str = ""
    registered_voters: str = ""


# --------------------------------------------------------------------- #
# 3. Contest
# --------------------------------------------------------------------- #
@dataclass
class Contest:
    title: str = ""                     # raw title from PDF
    party: Optional[str] = None         # contest-level party (Dem/Rep/…)
    overvotes: str = ""
    undervotes: str = ""
    candidates: List["CandidateResult"] = field(default_factory=list)

    # ---- extracted from title (cached internally) ----
    _modifier: str = ""
    _vote_for: str = "1"

    # -----------------------------------------------------------------
    # CSV-mapped properties (read-only)
    # -----------------------------------------------------------------
    @property
    def modifier(self) -> str:
        return self._modifier

    @property
    def vote_for(self) -> str:
        return self._vote_for

    @property
    def office(self) -> str:
        base = self.title.split(" - ", 1)[0]
        base = re.sub(r"\s*[\(\[]?(Vote|Elect|Choose|Top)\s+\d+[\)\]]?", "", base, flags=re.IGNORECASE)
        return base.strip()

    @property
    def district_name(self) -> str:
        return self.office

    @property
    def district_type(self) -> str:
        return self.office

    @property
    def number_of_winners(self) -> str:
        return self.vote_for


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


@dataclass
class Row:
    Event_Date: str = ""
    Event_Type: str = ""
    Precinct_Name: str = ""
    Vote_Channel: str = ""
    Candidate: str = ""
    Total_Votes: str = ""
    Total_Votes_Cast: str = ""
    District_Name: str = ""
    District_Type: str = ""
    Office: str = ""
    Office_Modifier: str = ""
    n_winners: str = "1"
    Total_Ballots_Cast: str = ""
    Over_Votes: str = "N/A"
    Undervotes: str = "N/A"
    Ballots_Cast: str = ""
    County: str = ""
    Raw_Title: str = ""
    Candidate_Party: str = ""
    Contest_Party: str = ""