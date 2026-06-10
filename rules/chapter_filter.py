# -*- coding: utf-8 -*-
"""ChapterFilterRule: document-level pre-filtering.

Merges logic from ``core/doc_filters.pre_filtering()``
and ``core/repetition``.
This is a *filter* rule — it may reject the context.

Note: ``is_needed_document()`` from the original code was never called
in ``transform.py`` and is therefore intentionally omitted.
"""

import logging
import re
import statistics
import zlib
from collections import Counter

from warc_zh_clean import config as C
from warc_zh_clean.models import CleanContext
from warc_zh_clean.rules.base import BaseRule

_log = logging.getLogger(__name__)

# Optional dependency: zhconv
try:
    import zhconv as _zhconv
    _ZHCONV_AVAILABLE = True
except ImportError:
    _zhconv = None
    _ZHCONV_AVAILABLE = False
    _log.warning("zhconv not available; fan2jian_distance check will be skipped")

# Optional dependency: Levenshtein
try:
    import Levenshtein as _Levenshtein
    _LEVENSHTEIN_AVAILABLE = True
except ImportError:
    _Levenshtein = None
    _LEVENSHTEIN_AVAILABLE = False
    _log.warning("Levenshtein not available; fan2jian_distance check will be skipped")


# ---------------------------------------------------------------------------
# Density-rule helpers
# ---------------------------------------------------------------------------

# Pre-compiled regex cache keyed by pattern string
_DENSITY_RE_CACHE: dict[str, re.Pattern] = {}


def _get_density_count(text: str, counter: str) -> int:
    """Return the hit count for a DensityRule counter spec against *text*."""
    if counter.startswith("substr:"):
        return text.count(counter[7:])
    if counter.startswith("regex:"):
        pat = counter[6:]
        if pat not in _DENSITY_RE_CACHE:
            _DENSITY_RE_CACHE[pat] = re.compile(pat)
        return len(_DENSITY_RE_CACHE[pat].findall(text))
    raise ValueError(f"Unknown counter format: {counter!r}")


def _check_density_rules(
    text: str,
    category: str,
    ctx_signals: dict,
) -> tuple[bool, str]:
    """Evaluate all MISC_DENSITY_RULES against *text*.

    Side-effect: writes triggered rule counts into *ctx_signals*.
    Returns (True, "") on pass, (False, detail) on first failure.
    """
    text_len = max(len(text), 1)
    for rule in C.MISC_DENSITY_RULES:
        if category in rule.category_exempt:
            continue
        count = _get_density_count(text, rule.counter)
        ctx_signals[f"density_{rule.name}"] = count
        if count >= rule.min_count and count / text_len * 1000 > rule.max_per_kilo:
            return False, f"density:{rule.name}={count}/{text_len}"
    return True, ""


def _check_bad_keyword_score(
    text: str,
    ctx_signals: dict,
) -> tuple[bool, str]:
    """Weighted bad-keyword scoring filter.

    Score = sum(min(text.count(kw), 5) * weight  for kw in BAD_KEYWORDS if kw in text).
    Rejects when score >= BAD_KEYWORD_SCORE_MIN  AND
               score / len(text) * 1000 > BAD_KEYWORD_SCORE_PER_KILO.
    """
    text_len = max(len(text), 1)
    score = 0.0
    for kw in C.BAD_KEYWORDS:
        if kw in text:
            weight = C.BAD_KEYWORD_WEIGHTS.get(kw, 1.0)
            score += min(text.count(kw), 5) * weight
    ctx_signals["bad_keyword_score"] = score
    if score >= C.BAD_KEYWORD_SCORE_MIN and score / text_len * 1000 > C.BAD_KEYWORD_SCORE_PER_KILO:
        return False, f"bad_keyword_score={score}/{text_len}"
    return True, ""


# ---------------------------------------------------------------------------
# Pure helper functions (no ctx dependency)
# ---------------------------------------------------------------------------


def _check_length(text: str) -> tuple[bool, str]:
    """Check minimum text length."""
    if len(text) <= C.MIN_TEXT_LEN:
        return False, "text_too_short"
    return True, ""


def _check_category(category: str) -> tuple[bool, str]:
    """Check category blocklist and downsampling."""
    if category in C.CATEGORY_BLOCKLIST:
        return False, "blocked_category"

    if C.ENABLE_CATEGORY_DOWNSAMPLE and category in C.CATEGORY_DOWNSAMPLE_RATIOS:
        import random

        ratio = C.CATEGORY_DOWNSAMPLE_RATIOS[category]
        if random.random() < 1 - ratio:
            return False, "category_downsampled"
    return True, ""


def _check_zlib(text: str) -> tuple[bool, str]:
    """Check zlib compression ratio for repetition detection."""
    raw = text.encode()

    # Empty text passes
    if len(raw) == 0:
        return True, ""

    compressed = zlib.compress(raw)
    meta_u = len(raw) / len(compressed)

    if meta_u >= C.ZLIB_FULL_THRESHOLD:
        return False, "zlib_full_high"

    # Skip block check for very short texts
    if len(raw) < C.ZLIB_BLOCK_MIN_RAW_LEN:
        return True, ""

    block_num = len(text) // C.ZLIB_BLOCK_SIZE + 1
    repeat_block = 0
    evaluated_blocks = 0
    for block_id in range(block_num):
        block_raw = text[block_id * C.ZLIB_BLOCK_SIZE : (block_id + 1) * C.ZLIB_BLOCK_SIZE].encode()
        if len(block_raw) < C.ZLIB_BLOCK_MIN_RAW_LEN:
            continue
        evaluated_blocks += 1
        block_compressed = zlib.compress(block_raw)
        block_meta_u = len(block_raw) / len(block_compressed)
        if block_meta_u > C.ZLIB_BLOCK_THRESHOLD:
            repeat_block += 1
    if evaluated_blocks > 0 and repeat_block >= max(C.ZLIB_REPEAT_BLOCK_MIN, int(evaluated_blocks * C.ZLIB_REPEAT_BLOCK_FRACTION)):
        return False, "zlib_block_high"

    return True, ""


def _check_get_element_by_id(text: str) -> tuple[bool, str]:
    """Check for JS artifact .getElementById."""
    if ".getElementById" in text and "`" not in text:
        return False, "js_artifact"
    return True, ""


def _check_duplicate_fraction(text: str) -> tuple[bool, str]:
    """Check duplicate line / paragraph / character fractions."""
    length_text = len(text)
    lines = [x for x in text.split("\n") if x.strip() != ""]
    length_lines = len(lines)
    paragraphs = [x for x in re.split("\n{2,}", text) if x.strip() != ""]
    length_paragraphs = len(paragraphs)

    line_dict = {}
    line_dedup_count = 0
    line_dedup_char_count = 0
    for line in lines:
        if line not in line_dict:
            line_dict[line] = None
        else:
            line_dedup_count += 1
            line_dedup_char_count += len(line)

    paragraph_dict = {}
    paragraph_dedup_count = 0
    paragraph_dedup_char_count = 0
    for paragraph in paragraphs:
        if paragraph not in paragraph_dict:
            paragraph_dict[paragraph] = 1
        else:
            paragraph_dedup_count += 1
            paragraph_dedup_char_count += len(paragraph)

    if line_dedup_count / max(length_lines, 1) > C.DUPLICATE_LINE_RATIO:
        return False, "duplicate_line_ratio"
    if line_dedup_char_count / max(length_text, 1) > C.DUPLICATE_LINE_CHAR_RATIO:
        return False, "duplicate_line_char_ratio"
    if paragraph_dedup_count / max(length_paragraphs, 1) > C.DUPLICATE_PARA_RATIO:
        return False, "duplicate_para_ratio"
    if paragraph_dedup_char_count / max(length_text, 1) > C.DUPLICATE_PARA_CHAR_RATIO:
        return False, "duplicate_para_char_ratio"

    return True, ""


def _has_frequent_ngram(tokens_filter, N, threshold):
    """Check if any N-gram exceeds the frequency threshold (early-exit)."""
    counter = {}
    for idx in range(len(tokens_filter) - N):
        gram = "_".join(tokens_filter[idx : idx + N])
        count = counter.get(gram, 0) + 1
        if count > threshold:
            return True
        counter[gram] = count
    return False


    if _has_frequent_ngram(tokens_filter, 5, C.PRE_NGRAM_5_THRESHOLD):
        return False, "ngram_5_high"
    try:
        if _has_frequent_ngram(tokens_filter, 15, C.PRE_NGRAM_15_THRESHOLD):
            return False, "ngram_15_high"
    except Exception:
        pass

    return True, ""


def _check_misc_counts(text: str, category: str, ctx_signals: "dict | None" = None) -> tuple[bool, str]:
    """Check structurally-fixed count-based pre-filtering rules.

    Rules that scale with document length have been migrated to
    MISC_DENSITY_RULES and are evaluated by _check_density_rules (called
    separately in ChapterFilterRule.apply).

    The bad-keyword filter is handled by _check_bad_keyword_score.

    Only structural checks that cannot be expressed as a simple
    substring/regex density remain here.
    """
    if ctx_signals is None:
        ctx_signals = {}

    lines = [x for x in text.split("\n") if x != "" and "|" not in x]
    spans = [x for x in re.split("，|。|？|！|；", text) if x != ""]
    if len(lines) == 0 or len(spans) == 0:
        return False, "no_lines_or_spans"

    # getElementById check (structural: combined with backtick guard)
    if ".getElementById" in text and "`" not in text:
        return False, "js_artifact_2"

    # Fan2jian distance (ratio, not a count)
    if _ZHCONV_AVAILABLE and _LEVENSHTEIN_AVAILABLE:
        fan2jian = _zhconv.convert(text, "zh-cn")
        if text != fan2jian and _Levenshtein.distance(text, fan2jian) / max(len(text), len(fan2jian)) > C.PRE_FAN2JIAN_DISTANCE_RATIO:
            return False, "fan2jian_distance_high"
    elif C.STRICT_OPTIONAL_DEPS:
        raise ImportError("zhconv and Levenshtein are required when STRICT_OPTIONAL_DEPS=True")

    # Date hits density (compound: count + char-ratio cannot be one DensityRule)
    date_hits = (
        re.findall(r"\d{4}-\d{1,2}-\d{1,2}\]", text)
        + re.findall(r"\[\d{2,}-\d{2}-\d{2}\]", text)
        + re.findall(r"\d{4}/\d{1,2}/\d{1,2}", text)
        + re.findall(r"\d{4}-\d{2}-\d{2}", text)
        + re.findall(r"\d{4}\.\d{2}\.\d{2}", text)
        + re.findall(r"\d{4}/\d{2}/\d{2}", text)
    )
    if len(date_hits) > C.PRE_DATE_HITS_COUNT_LIMIT and len("".join(date_hits)) > len(text) * C.PRE_DATE_HITS_CHAR_RATIO:
        return False, "date_hits_high"

    # Non-printable ratio (ratio, not a count)
    ratio = len([x for x in text if not x.isprintable()]) / max(len(text), 1)
    if ratio > C.PRE_NON_PRINTABLE_RATIO:
        return False, "non_printable_high"

    # Line length statistics (mean/max — structural)
    nline = [x for x in text.split("\n") if x.strip() != ""]
    if not nline:
        return False, "no_content_lines"
    line_len = [len(x) for x in nline]
    if max(line_len) <= C.PRE_MAX_LINE_LEN_LIMIT:
        return False, "line_len_too_short"
    if statistics.mean(line_len) <= C.PRE_MEAN_LINE_LEN_LIMIT:
        return False, "line_len_too_short"

    # Duplicate line count (most_common — structural)
    if Counter(nline).most_common(1)[0][1] > C.PRE_DUPLICATE_LINE_COUNT_LIMIT:
        return False, "duplicate_line_count_high"

    return True, ""



# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


class ChapterFilterRule(BaseRule):
    """Document-level pre-filtering rule.

    Checks minimum length, category, zlib compression, repetition,
    various count-based thresholds, density rules, and bad-keyword scoring.
    May reject the context with ``reject_reason="filter_rules_2"``.
    """

    def apply(self, ctx: CleanContext) -> CleanContext:
        # Structural checks first (fast-fail)
        structural_checks = [
            (_check_length, ctx.text, {}),
            (_check_category, ctx.category, {}),
            (_check_zlib, ctx.text, {}),
            (_check_get_element_by_id, ctx.text, {}),
            (_check_duplicate_fraction, ctx.text, {}),
            (_check_misc_counts, ctx.text, {"category": ctx.category, "ctx_signals": ctx.quality_signals}),
        ]

        for check_fn, arg, kwargs in structural_checks:
            passed, detail = check_fn(arg, **kwargs)
            if not passed:
                ctx.reject("filter_rules_2", detail)
                return ctx

        # Density rules (scalable count checks)
        passed, detail = _check_density_rules(ctx.text, ctx.category, ctx.quality_signals)
        if not passed:
            ctx.reject("filter_rules_2", detail)
            return ctx

        # Bad-keyword weighted scoring
        passed, detail = _check_bad_keyword_score(ctx.text, ctx.quality_signals)
        if not passed:
            ctx.reject("filter_rules_2", detail)
            return ctx

        return ctx
