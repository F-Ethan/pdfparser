# src/logger.py
import logging
from pathlib import Path
from typing import Optional
from .config import LOG_DIR


def get_logger(name: str = "pdf_extractor") -> logging.Logger:
    """
    Return a configured logger.

    * One console handler (INFO+)
    * One file handler (DEBUG+)
    * pdfplumber noise silenced
    """
    logger = logging.getLogger(name)

    # -----------------------------------------------------------------
    # Prevent double-configuration when the module is imported many times
    # -----------------------------------------------------------------
    if logger.handlers:
        return logger

    # -----------------------------------------------------------------
    # 1. Root logger level – capture everything
    # -----------------------------------------------------------------
    logger.setLevel(logging.DEBUG)          # <-- change from INFO to DEBUG

    # -----------------------------------------------------------------
    # 2. File handler – write DEBUG and above
    # -----------------------------------------------------------------
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_DIR / "pdf_extraction.log")
    fh.setLevel(logging.DEBUG)               # <-- DEBUG → file
    fh_fmt = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    fh.setFormatter(fh_fmt)
    logger.addHandler(fh)

    # -----------------------------------------------------------------
    # 3. Console handler – keep INFO+ (so you don’t flood the terminal)
    # -----------------------------------------------------------------
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)                # <-- console stays at INFO
    ch_fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(ch_fmt)
    logger.addHandler(ch)

    # -----------------------------------------------------------------
    # 4. Silence pdfplumber (unchanged)
    # -----------------------------------------------------------------
    logging.getLogger("pdfplumber").setLevel(logging.WARNING)

    return logger