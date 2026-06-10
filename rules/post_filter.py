# -*- coding: utf-8 -*-
"""Post-filter rules: PostLengthFilterRule and RatioFilterRule.

Merges logic from ``core/doc_filters.post_filtering()`` and the
length-ratio check from ``core/transform.py``.
These are *filter* rules — they may reject the context.
"""

import re

from warc_zh_clean import config as C
from warc_zh_clean.models import CleanContext
from warc_zh_clean.rules.base import BaseRule


# ---------------------------------------------------------------------------
# Pure helper functions (no ctx dependency)
# ---------------------------------------------------------------------------


def _post_filtering(text: str) -> tuple[bool, str]:
    """Apply post-filtering rules after line-level cleaning.

    Returns:
        (passed, detail) tuple.
    """
    new_lines = text.split("\n")

    # Bullet line ratio
    list_len = len([x for x in new_lines if x.strip().startswith("•")])
    if list_len > C.POST_BULLET_LINE_RATIO * len(new_lines) and list_len > C.POST_BULLET_LINE_MIN:
        return False, "post_bullet_ratio_high"

    # Long sentence detection
    split_sents = C.POST_SPLIT_RE.split(text)
    if max((len(x) for x in split_sents), default=0) >= C.POST_LONG_SENT_LEN:
        return False, "post_long_sentence"

    # Time HH:MM density
    if len(C.TIME_HHMM_RE.findall(text)) >= C.POST_TIME_HHMM_LIMIT:
        return False, "post_time_hhmm_high"

    # Truncated line ratio
    truncline = C.TRUNC_LINE_RE.findall(text)
    if len(truncline) > 2 and len(truncline) >= len([x for x in text.split("\n") if x.strip() != ""]) * C.POST_TRUNC_LINE_RATIO:
        return False, "post_trunc_line_high"

    # Minimum text length re-check
    if len(text) <= C.MIN_TEXT_LEN:
        return False, "post_text_too_short"

    return True, ""


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


class PostLengthFilterRule(BaseRule):
    """Post-cleaning length filter.

    Checks bullet ratio, long sentences, time density, truncated lines,
    and minimum text length after line-level cleaning.
    May reject the context with ``reject_reason="post_filter"``.
    """

    def apply(self, ctx: CleanContext) -> CleanContext:
        passed, detail = _post_filtering(ctx.text)
        if not passed:
            ctx.reject("post_filter", detail)
        return ctx


class RatioFilterRule(BaseRule):
    """Length ratio filter.

    Checks ``len(text) / text_len < threshold`` after line-level cleaning.
    May reject the context with ``reject_reason="ratio_filter"``.
    """

    def apply(self, ctx: CleanContext) -> CleanContext:
        if ctx.text_len == 0:
            ctx.reject("ratio_filter", "text_len_is_zero")
            return ctx

        ctx.text_length_ratio = len(ctx.text) / (ctx.text_len + C.LENGTH_RATIO_EPSILON)
        if ctx.text_length_ratio < C.FINAL_TEXT_LENGTH_RATIO_THRESHOLD:
            ctx.reject("ratio_filter", f"ratio={ctx.text_length_ratio:.3f}<{C.FINAL_TEXT_LENGTH_RATIO_THRESHOLD}")
        return ctx