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
        """
        Export the full hierarchy to CSV rows.
        One row per candidate per vote channel (Total, Early, Absentee, Election Day).
        """
        rows = []

        for precinct in self.precincts:
            for contest in precinct.contests:
                for cand in contest.candidates:
                    # Define all possible channels with their vote counts
                    channels = [
                        ("Early", cand.early_votes),
                        ("Absentee", cand.absentee_votes),
                        ("Election Day", cand.election_day_votes),
                        ("Total", cand.total_votes),
                    ]

                    for channel, votes in channels:

                        rows.append({
                            "Event Date": self.date,
                            "Event Type": self.election_type or 'N/A',
                            "County": self.county,
                            "Precinct Name": precinct.number,
                            "Vote Channel": channel,
                            "Candidate": cand.name,
                            "Votes": votes,                    
                            "Total Votes Cast": contest.cast_votes,
                            "Office": contest.office,
                            "District Name": contest.title,
                            "District Type": contest.title,
                            "Office Modifier": contest.modifier,
                            "# of winners": contest.vote_for,
                            "Total Ballots Cast": self.total_ballots,
                            "Ballots Cast": precinct.ballots_cast,
                            "Over Votes": contest.overvotes or 'N/A',
                            "Undervotes": contest.undervotes or 'N/A',
                            "Candidate Party": cand.party or "",
                            "Contest Party": contest.party or self.party,
                            "Raw Title": contest.title,
                        })

        return rows
    
    # In EventData
    def contest_to_rows(self, precinct: Precinct, contest: Contest) -> List[dict]:
        rows = []
        for cand in contest.candidates:
            channels = [
                ("Early", cand.early_votes),
                ("Absentee", cand.absentee_votes),
                ("Election Day", cand.election_day_votes),
                ("Total", cand.total_votes),
            ]
            for channel, votes in channels:
                rows.append({
                    "Event Date": self.date,
                    "Event Type": self.election_type or 'N/A',
                    "County": self.county,
                    "Precinct Name": precinct.number,
                    "Vote Channel": channel,
                    "Candidate": cand.name,
                    "Votes": votes,                    
                    "Total Votes Cast": contest.cast_votes,
                    "Office": contest.office,
                    "District Name": contest.office,
                    "District Type": contest.office,
                    "Office Modifier": contest.modifier,
                    "# of winners": contest.vote_for,
                    "Total Ballots Cast": self.total_ballots,
                    "Ballots Cast": precinct.ballots_cast,
                    "Over Votes": contest.overvotes or 'N/A',
                    "Undervotes": contest.undervotes or 'N/A',
                    "Candidate Party": cand.party or "",
                    "Contest Party": contest.party or self.party,
                    "Raw Title": contest.title,
                })
        return rows


# --------------------------------------------------------------------- #
# 2. Precinct
# --------------------------------------------------------------------- #
@dataclass
class Precinct:
    number: str
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
    cast_votes: str = ""
    overvotes: str = ""
    undervotes: str = ""
    modifier: str = ""

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