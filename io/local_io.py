# -*- coding: utf-8 -*-
"""Local JSONL IO utilities."""

import json
from typing import Iterable, Iterator


def read_jsonl(path: str) -> Iterator[dict]:
    """Read local JSONL file.

    Args:
        path: Local JSONL file path.

    Yields:
        Parsed JSON record.
    """
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_jsonl(records: Iterable[dict], path: str) -> None:
    """Write records to local JSONL file.

    Args:
        records: Records to write.
        path: Output JSONL file path.
    """
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")