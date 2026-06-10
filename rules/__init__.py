# -*- coding: utf-8 -*-
"""Rule subpackage for the IoC pipeline."""

from warc_zh_clean.rules.base import BaseRule
from warc_zh_clean.rules.pre_clean import PreCleanRule
from warc_zh_clean.rules.chapter_filter import ChapterFilterRule
from warc_zh_clean.rules.line_clean import LineCleanRule
from warc_zh_clean.rules.post_filter import PostLengthFilterRule, RatioFilterRule

__all__ = [
    "BaseRule",
    "PreCleanRule",
    "ChapterFilterRule",
    "LineCleanRule",
    "PostLengthFilterRule",
    "RatioFilterRule",
]