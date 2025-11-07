# src/config.py
from pathlib import Path
from typing import Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"
OUTPUT_CSV = OUTPUT_DIR / "Election_Results.csv"

# --------------------------------------------------------------------- #
# Runtime configuration
# --------------------------------------------------------------------- #
IN_DEVELOPMENT: bool = True
BATCH_SIZE: int = 300
DEBUG_PAGE_RANGE: Optional[Tuple[int, int]] = None  # e.g. (50, 70)
PARTY_BY_FILE: bool = False
SET_FIX_DATE: str = ""
SET_FIX_BALLOTS_CAST: str = ""
REGULAR_EXPRESSION: bool = True