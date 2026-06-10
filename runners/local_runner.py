# -*- coding: utf-8 -*-
"""Local runner for debugging without Spark."""

from warc_zh_clean.pipelines import build_cleaner_pipeline
from warc_zh_clean.io.local_io import read_jsonl, write_jsonl


def run_local(input_path: str, output_path: str) -> None:
    """Run the cleaning pipeline locally on a JSONL file.

    Args:
        input_path: Local input JSONL path.
        output_path: Local output JSONL path.
    """
    pipeline = build_cleaner_pipeline()
    output_records = []

    for record in read_jsonl(input_path):
        text = record.get("text")
        if not isinstance(text, str) or not text.strip():
            continue

        result = pipeline.process(record)
        if result.clean_rec is not None:
            output_records.append(result.clean_rec)

    write_jsonl(output_records, output_path)

    print(f"[OK] local output written to: {output_path}")
    print(f"[OK] records: {len(output_records)} kept")