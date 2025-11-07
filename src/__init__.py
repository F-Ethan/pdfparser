# src/__init__.py
"""
Make the `src` directory a proper Python package.
This file allows:
    from src import Event
    from src.models import Precinct, Contest
    from src.contest import ContestParser
"""

# Core domain objects
from .models import (
    EventData,
    Precinct,
    Contest,
    CandidateResult,
)

# Main parser entry point
from .event import EventParser

# Specialized parsers
from .precinct import PrecinctParser
from .contest import ContestParser

# Optional: version or metadata
__version__ = "0.1.0"
__all__ = [
    "EventData",
    "Precinct",
    "Contest",
    "CandidateResult",
    "Event",
    "PrecinctParser",
    "ContestParser",
]