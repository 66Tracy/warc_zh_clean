# -*- coding: utf-8 -*-
"""Explicit registry for rule classes and hook handlers.

This is the single "wiring" module — all class-name-to-class mappings
are declared here. No dynamic imports.
"""

from warc_zh_clean.rules.pre_clean import PreCleanRule
from warc_zh_clean.rules.chapter_filter import ChapterFilterRule
from warc_zh_clean.rules.line_clean import LineCleanRule
from warc_zh_clean.rules.post_filter import PostLengthFilterRule, RatioFilterRule
from warc_zh_clean.pipelines.hooks import set_text_len


# Rule class registry: YAML class name -> class object
RULE_REGISTRY = {
    "PreCleanRule": PreCleanRule,
    "ChapterFilterRule": ChapterFilterRule,
    "LineCleanRule": LineCleanRule,
    "PostLengthFilterRule": PostLengthFilterRule,
    "RatioFilterRule": RatioFilterRule,
}


# Hook handler registry: YAML handler name -> callable
HOOK_REGISTRY = {
    "set_text_len": set_text_len,
}