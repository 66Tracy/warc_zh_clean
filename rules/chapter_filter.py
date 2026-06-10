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


def _check_ngram(text: str) -> tuple[bool, str]:
    """Check N-gram repetition (5-gram and 15-gram)."""
    tokens_filter = [x for x in text if x not in [" ", "\n", "-", "|"]]
    if len(tokens_filter) < 5:
        return True, ""

    if _has_frequent_ngram(tokens_filter, 5, C.PRE_NGRAM_5_THRESHOLD):
        return False, "ngram_5_high"
    try:
        if _has_frequent_ngram(tokens_filter, 15, C.PRE_NGRAM_15_THRESHOLD):
            return False, "ngram_15_high"
    except Exception:
        pass

    return True, ""


def _check_misc_counts(text: str, category: str) -> tuple[bool, str]:
    """Check various count-based pre-filtering rules."""
    lines = [x for x in text.split("\n") if x != "" and "|" not in x]
    spans = [x for x in re.split("，|。|？|！|；", text) if x != ""]
    if len(lines) == 0 or len(spans) == 0:
        return False, "no_lines_or_spans"

    # Ellipsis line density
    if len([x for x in lines if x.endswith("...") or x.endswith("…")]) > C.PRE_ELLIPSIS_LINE_LIMIT:
        return False, "ellipsis_line_high"

    # Datetime density
    if len(re.findall(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text)) >= C.PRE_DATETIME_DENSITY_LIMIT:
        return False, "datetime_density_high"

    # Blank zh-zh patterns
    if len(re.findall(r"[\u4e00-\u9fff]\s[\u4e00-\u9fff]", text)) > C.PRE_BLANK_ZH_ZH_LIMIT:
        return False, "blank_zh_zh_high"

    # Language transition patterns
    if len(re.findall(r"[\u4e00-\u9fff][a-zA-Z][\u4e00-\u9fff]", text)) > C.PRE_LANG_TRANS_LIMIT:
        return False, "lang_trans_high"

    # Ellipsis count
    if text.replace(" ", "").count("...") >= C.PRE_ELLIPSIS_COUNT_LIMIT:
        return False, "ellipsis_count_high"

    # getElementById check (second pass, combined with ellipsis check)
    if ".getElementById" in text and "`" not in text:
        return False, "js_artifact_2"

    # Fan2jian distance
    if _ZHCONV_AVAILABLE and _LEVENSHTEIN_AVAILABLE:
        fan2jian = _zhconv.convert(text, "zh-cn")
        if text != fan2jian and _Levenshtein.distance(text, fan2jian) / max(len(text), len(fan2jian)) > C.PRE_FAN2JIAN_DISTANCE_RATIO:
            return False, "fan2jian_distance_high"
    elif C.STRICT_OPTIONAL_DEPS:
        raise ImportError("zhconv and Levenshtein are required when STRICT_OPTIONAL_DEPS=True")

    # Date hits density
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

    # MB pattern
    if len(re.findall(r"\d+mb|\d+ mb", text.lower())) > C.PRE_MB_PATTERN_LIMIT and category != "编程/IT":
        return False, "mb_pattern_high"

    # Empty parens
    if text.count("()") >= C.PRE_EMPTY_PAREN_LIMIT and category != "编程/IT" and "`" not in text:
        return False, "empty_paren_high"

    # Question marks
    if text.count("吗？") >= C.PRE_QUESTION_MARK_LIMIT:
        return False, "question_mark_high"

    # Non-printable ratio
    ratio = len([x for x in text if not x.isprintable()]) / len(text)
    if ratio > C.PRE_NON_PRINTABLE_RATIO:
        return False, "non_printable_high"

    # Bad keyword hits
    bad_keyword_hits = 0
    for keyword in C.BAD_KEYWORDS:
        if keyword in text:
            bad_keyword_hits += 1
            if bad_keyword_hits >= C.BAD_KEYWORD_HIT_THRESHOLD:
                return False, "bad_keyword_hit"

    # Various count-based checks
    if (
        text.count("天前回复") >= C.PRE_REPLY_DAY_LIMIT
        or text.count("！") + text.count("？") >= C.PRE_EXCL_QUESTION_LIMIT
        or text.count("座") >= C.PRE_SEAT_LIMIT
        or text.count("分钟前回复") >= C.PRE_REPLY_MIN_LIMIT
        or text.count("小时前回复") >= C.PRE_REPLY_HOUR_LIMIT
        or text.count("澳门") >= C.PRE_MACAO_LIMIT
        or text.count("癫痫病") >= C.PRE_EPILEPSY_LIMIT
        or text.count("【") >= C.PRE_BRACKET_LIMIT
        or text.count("彩票") >= C.PRE_LOTTERY_LIMIT
        or text.count("买球") >= C.PRE_BET_LIMIT
    ):
        return False, "count_threshold_exceeded"

    # Line length statistics
    nline = [x for x in text.split("\n") if x.strip() != ""]
    if not nline:
        return False, "no_content_lines"
    line_len = [len(x) for x in nline]
    if max(line_len) <= C.PRE_MAX_LINE_LEN_LIMIT:
        return False, "line_len_too_short"
    if statistics.mean(line_len) <= C.PRE_MEAN_LINE_LEN_LIMIT:
        return False, "line_len_too_short"

    # Duplicate line count
    if Counter(nline).most_common(1)[0][1] > C.PRE_DUPLICATE_LINE_COUNT_LIMIT:
        return False, "duplicate_line_count_high"

    # Placeholder counts
    if (
        text.count("<URL>") > C.PRE_URL_COUNT_LIMIT
        or text.count("<EMAIL>") > C.PRE_EMAIL_COUNT_LIMIT
        or text.count("QQ") > C.PRE_QQ_COUNT_LIMIT
        or text.count("微信") > C.PRE_WECHAT_COUNT_LIMIT
        or text.count("…") >= C.PRE_ELLIPSIS_UNICODE_LIMIT
        or text.count("...") >= C.PRE_ELLIPSIS_ASCII_LIMIT
    ):
        return False, "placeholder_count_high"

    # Date bracket pattern
    if len(re.findall(r"\[\d{2}-\d{2}\]", text)) >= C.PRE_DATE_BRACKET_LIMIT:
        return False, "date_bracket_high"

    return True, ""


def _check_basic_quality(text: str) -> tuple[bool, str]:
    """Check basic document quality (is_needed_document logic)."""
    if len(text) == 0:
        return True, ""

    lines = text.split("\n")
    length_lines = len(lines)

    if len(text.split()) / len(text) > C.WHITESPACE_RATIO_MAX:
        return False, "whitespace_ratio_high"

    fuhao_zifu_rate = len(re.findall("[^\u4E00-\u9FA5]", text)) / len(text)
    if fuhao_zifu_rate > C.NON_CJK_RATIO_MAX:
        return False, "non_cjk_ratio_high"

    count_bullet_line = sum(1 for line in lines if line.strip().startswith("•"))
    if count_bullet_line / max(length_lines, 1) >= C.BULLET_LINE_RATIO_MAX:
        return False, "bullet_line_ratio_high"

    count_bullet_line_2 = sum(1 for line in lines if line.strip().startswith("-"))
    if count_bullet_line_2 / max(length_lines, 1) >= C.BULLET_LINE_RATIO_MAX:
        return False, "dash_bullet_ratio_high"

    count_ellipsis = sum(
        1
        for line in lines
        if line.strip().endswith("...") or line.strip().endswith("…") or line.strip().endswith("[…]")
    )
    if count_ellipsis / max(length_lines, 1) > C.ELLIPSIS_LINE_RATIO_MAX:
        return False, "ellipsis_line_ratio_high"

    return True, ""


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


class ChapterFilterRule(BaseRule):
    """Document-level pre-filtering rule.

    Checks minimum length, category, zlib compression, repetition,
    various count-based thresholds, and N-gram patterns.
    May reject the context with ``reject_reason="filter_rules_2"``.
    """

    def apply(self, ctx: CleanContext) -> CleanContext:
        checks = [
            (_check_length, ctx.text, {}),
            (_check_category, ctx.category, {}),
            (_check_zlib, ctx.text, {}),
            (_check_get_element_by_id, ctx.text, {}),
            (_check_duplicate_fraction, ctx.text, {}),
            (_check_misc_counts, ctx.text, {"category": ctx.category}),
            (_check_ngram, ctx.text, {}),
        ]

        for check_fn, arg, kwargs in checks:
            passed, detail = check_fn(arg, **kwargs)
            if not passed:
                ctx.reject("filter_rules_2", detail)
                return ctx

        return ctx