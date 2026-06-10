# -*- coding: utf-8 -*-
"""Spark runner for YARN cluster execution."""

import json
from typing import Iterator

from warc_zh_clean.pipelines import build_cleaner_pipeline


def _process_partition(rows) -> Iterator[str]:
    """Process one Spark partition.

    Initializes the pipeline once per partition to avoid serialization issues.

    Args:
        rows: Iterator of Spark Row objects.

    Yields:
        JSON string of processed records.
    """
    pipeline = build_cleaner_pipeline()

    for row in rows:
        try:
            record = row.asDict(recursive=True)

            text = record.get("text")
            if not isinstance(text, str) or not text.strip():
                continue

            result = pipeline.process(record)
            if result.clean_rec is not None:
                yield json.dumps(result.clean_rec, ensure_ascii=False)

        except Exception:
            continue


def run_spark(
    input_path: str,
    output_path: str,
    input_type: str = "json",
    output_type: str = "json",
) -> None:
    """Run the cleaning pipeline on Spark.

    Args:
        input_path: Spark input path (comma-separated for multiple paths).
        output_path: Spark output path.
        input_type: Input format, json or parquet.
        output_type: Output format, json or parquet.
    """
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()

    df = spark.read.format(input_type).load(input_path)
    df = df.dropna(subset=["text"])

    output_json_rdd = df.rdd.mapPartitions(_process_partition)
    output_df = spark.read.json(output_json_rdd)

    output_df.write.mode("overwrite").format(output_type).save(output_path)

    spark.stop()