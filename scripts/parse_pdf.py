#!/usr/bin/env python
"""
Main PDF → CSV extractor – works with your existing parser classes.
"""
import gc
from pathlib import Path
from typing import List, Optional

import pdfplumber
from tqdm import tqdm

# --------------------------------------------------------------------- #
# Project imports
# --------------------------------------------------------------------- #
from src.config import (
    INPUT_DIR,
    OUTPUT_DIR,
    OUTPUT_CSV,
    IN_DEVELOPMENT,
    DEBUG_PAGE_RANGE,
    BATCH_SIZE,
)
from src.logger import get_logger
from src.writer import CSVWriter
from src.event import EventParser
from src.precinct import PrecinctParser
from src.contest import ContestParser
from src.candidate import CandidateParser
from src.utils import group_words_into_lines

log = get_logger()

# --------------------------------------------------------------------- #
# Helper: page → clean lines
# --------------------------------------------------------------------- #
def page_to_lines(page) -> List[str]:
    text = page.extract_text()
    if text:
        return [ln.strip() for ln in text.splitlines() if ln.strip()]

    words = page.extract_words()
    return group_words_into_lines(words) if words else []


# --------------------------------------------------------------------- #
# Core extraction per PDF
# --------------------------------------------------------------------- #
def extract_pdf(pdf_path: Path, writer: CSVWriter) -> None:
    log.info(f"START {pdf_path.name}")

    # ----------------------------------------------------------------- #
    # 1. Event (first ~15 lines of page 1)
    # ----------------------------------------------------------------- #
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        first_lines = page_to_lines(first_page)[:15]

        event_parser = EventParser(first_lines)      # <-- uses your __init__
        event = event_parser.data
        log.info(f"Event → {event}")

        # ----------------------------------------------------------------- #
        # 2. Page range
        # ----------------------------------------------------------------- #
        total_pages = len(pdf.pages)
        max_page = 10 if IN_DEVELOPMENT else total_pages
        if DEBUG_PAGE_RANGE:
            start, end = DEBUG_PAGE_RANGE
            page_range = range(start, min(end, total_pages) + 1)
        else:
            page_range = range(1, max_page + 1)

        # ----------------------------------------------------------------- #
        # 3. State that lives across pages
        # ----------------------------------------------------------------- #
        current_precinct: Optional[PrecinctParser] = None
        buffer: List[str] = []

        # ----------------------------------------------------------------- #
        # 4. Page loop
        # ----------------------------------------------------------------- #
        for pno in tqdm(page_range, desc=pdf_path.stem, unit="page", leave=False):
            page = pdf.pages[pno - 1]
            lines = page_to_lines(page)

            # ---- precinct detection (your PrecinctParser) ----
            precinct = PrecinctParser.parse("\n".join(lines))
            if precinct:
                current_precinct = precinct
                # give the precinct to the contest parser (if it needs it)
                ContestParser.set_current_precinct(precinct)

            # ---- line-by-line buffer logic ----
            for line in lines:
                if ContestParser.is_contest_title(line):
                    # ---- process the *previous* block (if any) ----
                    if buffer:
                        _process_buffer(buffer, event, current_precinct, writer)
                    # start a fresh buffer with the new title
                    buffer = [line]
                else:
                    buffer.append(line)

            # occasional GC
            if pno % 50 == 0:
                gc.collect()

        # ---- final buffer (last contest on the last page) ----
        if buffer:
            _process_buffer(buffer, event, current_precinct, writer)

    log.info(f"FINISHED {pdf_path.name}")


# --------------------------------------------------------------------- #
# Process one contest block → rows → CSV
# --------------------------------------------------------------------- #
def _process_buffer(
    buffer: List[str],
    event: EventParser.data.__class__,   # EventData
    precinct: Optional[PrecinctParser],
    writer: CSVWriter,
) -> None:
    if not buffer:
        return

    title_line = buffer[0]
    candidate_block = buffer[1:]                     # everything after the title

    # 1. Parse contest title
    contest = ContestParser.parse_title(title_line)
    if not contest:
        log.warning(f"Could not parse contest title: {title_line[:80]}")
        return

    # 2. Parse candidate lines inside the block
    candidates = CandidateParser.parse(candidate_block, contest)

    # 3. Build CSV rows (4 channels per candidate)
    rows = CandidateParser.build_rows(
        candidates=candidates,
        event=event,
        precinct=precinct,
        contest=contest,
    )

    # 4. Write
    writer.add_rows(rows)


# --------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------- #
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_CSV.exists():
        OUTPUT_CSV.unlink()
        log.info(f"Deleted previous output: {OUTPUT_CSV}")

    writer = CSVWriter(batch_size=BATCH_SIZE)

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdf_files:
        log.warning("No PDF files found in INPUT_DIR")
        return

    for pdf_path in pdf_files:
        extract_pdf(pdf_path, writer)

    writer.flush()
    print(f"\nAll done! → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()