# src/logger.py
import logging
from pathlib import Path
from .config import LOG_DIR

# Global: prevent re-configuring the same logger
_CONFIGURED_LOGGERS = set()

def get_logger(name: str = "pdf_extractor") -> logging.Logger:
    """
    Return a configured logger.
    - Console: INFO+
    - File:    DEBUG+
    - No double handlers
    - pdfplumber silenced
    """
    logger = logging.getLogger(name)

    # -----------------------------------------------------------------
    # Prevent double-configuration
    # -----------------------------------------------------------------
    if name in _CONFIGURED_LOGGERS:
        return logger

    # -----------------------------------------------------------------
    # 1. Set level & clear any existing handlers
    # -----------------------------------------------------------------
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()  # ← CRITICAL: remove any parent/default handlers

    # -----------------------------------------------------------------
    # 2. File handler – DEBUG+
    # -----------------------------------------------------------------
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_DIR / "pdf_extraction.log")
    fh.setLevel(logging.DEBUG)
    fh_fmt = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    fh.setFormatter(fh_fmt)
    logger.addHandler(fh)

    # -----------------------------------------------------------------
    # 3. Console handler – INFO+
    # -----------------------------------------------------------------
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(ch_fmt)
    logger.addHandler(ch)

    # -----------------------------------------------------------------
    # 4. Silence pdfplumber
    # -----------------------------------------------------------------
    logging.getLogger("pdfplumber").setLevel(logging.WARNING)

    # -----------------------------------------------------------------
    # 5. Mark as configured
    # -----------------------------------------------------------------
    _CONFIGURED_LOGGERS.add(name)

    return logger