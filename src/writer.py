# src/writer.py
from pathlib import Path
from typing import List, Any
import pandas as pd
from .config import OUTPUT_CSV

# Row is GONE — we use dicts directly

class CSVWriter:
    def __init__(self, path: Path = OUTPUT_CSV, batch_size: int = 300):
        self.path = path
        self.batch_size = batch_size
        self.buffer: List[dict] = []
        self.headers_written = False

    def add_rows(self, rows: List[dict]) -> None:
        """Accept list of dicts (from CandidateParser.build_rows or EventData.to_csv_rows)"""
        self.buffer.extend(rows)
        if len(self.buffer) >= self.batch_size:
            self._write()

    def flush(self) -> None:
        if self.buffer:
            self._write()
            self.buffer.clear()  # ensure empty after flush

    def _write(self) -> None:
        if not self.buffer:
            return

        df = pd.DataFrame(self.buffer)

        # Write mode: 'w' first time, 'a' after
        mode = "a" if self.headers_written and self.path.exists() else "w"
        header = not self.headers_written

        df.to_csv(self.path, mode=mode, header=header, index=False)

        self.headers_written = True
        self.buffer.clear()