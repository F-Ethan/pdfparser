#!/usr/bin/env python
"""
Main PDF → CSV extractor – hierarchical, clean, no static state.
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
from src.models import EventData, Precinct, Contest, CandidateResult
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
def extract_pdf(pdf_path: Path, writer: CSVWriter) -> EventData:
    log.info(f"START {pdf_path.name}")
    print(f"START: {pdf_path.name}")

    with pdfplumber.open(pdf_path) as pdf:
        # -----------------------------------------------------------------
        # 1. Parse Event from first page
        # -----------------------------------------------------------------
        first_page = pdf.pages[0]
        first_lines = page_to_lines(first_page)[:15]
        event_parser = EventParser(first_lines, filename=pdf_path.name)
        event: EventData = event_parser.parse()  # EventData with empty precincts
        event.precincts = []  # ensure list is mutable

        # -----------------------------------------------------------------
        # 2. Page range
        # -----------------------------------------------------------------
        total_pages = len(pdf.pages)
        max_page = 10 if IN_DEVELOPMENT else total_pages

        if DEBUG_PAGE_RANGE:
            start, end = DEBUG_PAGE_RANGE
            # Clamp to actual page count
            start = max(1, start)
            end = min(end, total_pages)
            page_range = range(start, end + 1)
        else:
            page_range = range(1, min(max_page, total_pages) + 1)  # ← CRITICAL FIX

        # -----------------------------------------------------------------
        # 3. State for current context
        # -----------------------------------------------------------------
        current_precinct: Optional[Precinct] = None
        buffer: List[str] = []

        
        # -----------------------------------------------------------------
        # 4. Page loop – build hierarchy
        # -----------------------------------------------------------------
        for pno in tqdm(page_range, desc=pdf_path.stem, unit="page", leave=False):
            if pno > total_pages:
                log.warning(f"Skipping page {pno} > total pages ({total_pages})")
                continue
            page = pdf.pages[pno - 1]
            lines = page_to_lines(page)

            for line in lines:
                # --- 1. Detect new precinct ---
                if precinct := PrecinctParser.parse(line):
                    # Save previous contest block
                    if current_precinct and buffer:
                        _save_buffer(buffer, event, current_precinct, writer)
                        buffer = []

                    # Start new precinct
                    current_precinct = precinct
                    current_precinct.event = event
                    current_precinct.contests = []
                    event.precincts.append(current_precinct)
                    continue  # skip to next line

                # --- 2. Detect new contest title ---
                if current_precinct and ContestParser.is_contest_title(line):
                    if buffer:
                        _save_buffer(buffer, event, current_precinct, writer)
                    buffer = [line]  # start new contest block
                elif buffer:
                    buffer.append(line)

            # GC every 50 pages
            if pno % 50 == 0:
                gc.collect()

        # --- Final contest block ---
        if buffer and current_precinct:
            _save_buffer(buffer, event, current_precinct, writer)

    log.info(f"FINISHED {pdf_path.name}")
    return event  # ← full hierarchy


# --------------------------------------------------------------------- #
# Process one contest block → build hierarchy + CSV
# --------------------------------------------------------------------- #
def _save_buffer(
    buffer: List[str],
    event: EventData,
    precinct: Precinct,
    writer: CSVWriter,
) -> None:
    if not buffer:
        return

    title_line = buffer[0]
    candidate_lines = buffer[1:]

    # -----------------------------------------------------------------
    # 1. Parse Contest Title → Create Contest object
    # -----------------------------------------------------------------
    contest = ContestParser.parse_title(title_line)
    if not contest:
        log.warning(f"Could not parse contest title: {title_line[:80]}")
        return

    # Link contest to precinct
    contest.precinct = precinct
    precinct.contests.append(contest)
    contest.candidates = []  # initialize

    # -----------------------------------------------------------------
    # 2. Parse Candidate Block → List[CandidateResult]
    # -----------------------------------------------------------------
    candidates = CandidateParser.parse_block(
        lines=candidate_lines,
        contest=contest,           # for over/undervotes
        event_party=event.party    # fallback party
    )

    # Link candidates
    for cand in candidates:
        cand.contest = contest
        contest.candidates.append(cand)

    # -----------------------------------------------------------------
    # 3. Build and write CSV rows
    # -----------------------------------------------------------------
    rows = CandidateParser.build_rows(
        candidates=candidates,
        event=event,
        precinct=precinct,
        contest=contest,
    )
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
    all_events: List[EventData] = []

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdf_files:
        log.warning("No PDF files found in INPUT_DIR")
        return

    # Process each PDF
    for pdf_path in pdf_files:
        event = extract_pdf(pdf_path, writer)
        all_events.append(event)

    # Final CSV from full hierarchy
    all_rows = []
    for event in all_events:
        all_rows.extend(event.to_csv_rows())

    import pandas as pd
    df = pd.DataFrame(all_rows)
    df.to_csv(OUTPUT_CSV, index=False)
    log.info(f"Final CSV written: {OUTPUT_CSV} ({len(df):,} rows)")

    writer.flush()
    print(f"\nAll done! → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()