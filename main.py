# -*- coding: utf-8 -*-
"""Project entry point."""

import argparse


def main() -> None:
    """Parse arguments and dispatch runner."""
    parser = argparse.ArgumentParser(description="warc_zh_clean: Chinese WARC data post-cleaning pipeline")

    parser.add_argument(
        "--mode",
        choices=["local", "spark"],
        default="local",
        help="Run mode: local for JSONL debugging, spark for YARN cluster",
    )
    parser.add_argument("--input_path", required=True, help="Input path (comma-separated for spark mode)")
    parser.add_argument("--output_path", required=True, help="Output path")
    parser.add_argument(
        "--input_type",
        choices=["json", "parquet"],
        default="json",
        help="Input format for Spark mode",
    )
    parser.add_argument(
        "--output_type",
        choices=["json", "parquet"],
        default="json",
        help="Output format for Spark mode",
    )

    args = parser.parse_args()

    if args.mode == "local":
        from warc_zh_clean.runners.local_runner import run_local

        run_local(input_path=args.input_path, output_path=args.output_path)
    else:
        from warc_zh_clean.runners.spark_runner import run_spark

        run_spark(
            input_path=args.input_path,
            output_path=args.output_path,
            input_type=args.input_type,
            output_type=args.output_type,
        )


if __name__ == "__main__":
    main()