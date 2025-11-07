# src/logger.py
import logging
from .config import LOG_DIR

def get_logger(name: str = "pdf_extractor") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    LOG_DIR.mkdir(exist_ok=True)
    fh = logging.FileHandler(LOG_DIR / "pdf_extraction.log")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)

    # Reduce pdfplumber noise
    logging.getLogger("pdfplumber").setLevel(logging.WARNING)
    return logger