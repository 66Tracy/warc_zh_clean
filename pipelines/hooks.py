# -*- coding: utf-8 -*-
"""Pipeline hook functions."""

from warc_zh_clean.models import CleanContext


def set_text_len(ctx: CleanContext) -> CleanContext:
    """Hook: snapshot text length before line-level cleaning.

    This value is used later by RatioFilterRule to compute the
    text_length_ratio = len(text_after) / text_len.
    """
    ctx.text_len = len(ctx.text)
    return ctx