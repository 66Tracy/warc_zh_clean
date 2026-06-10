# -*- coding: utf-8 -*-
"""QualitySignalsRule: CCNet/Gopher/RefinedWeb quality signals adapted for Chinese.

Each signal is measured, written to ``ctx.quality_signals``, and compared
against the threshold in ``config.QUALITY_THRESHOLDS``.  The rule rejects
on the *first* signal that exceeds its threshold and stops further checks.

Setting a threshold field to ``None`` in ``QualityThresholds`` disables that
individual check without touching any others.
"""

from __future__ import annotations

import re
from collections import Counter

from warc_zh_clean import config as C
from warc_zh_clean.models import CleanContext
from warc_zh_clean.rules.base import BaseRule

# ---------------------------------------------------------------------------
# Pre-compiled patterns (no magic numbers in rule logic)
# ---------------------------------------------------------------------------

# CJK Unified Ideographs (U+4E00–U+9FFF) + Extension A (U+3400–U+4DBF) +
# Extension B (U+20000–U+2A6DF) – approximated by the common BMP block that
# covers 99 %+ of modern Chinese text – plus common CJK punctuation.
_CJK_RE = re.compile(
    r"[一-鿿"           # CJK Unified
    r"㐀-䶿"            # CJK Extension A
    r"　-〿"            # CJK Symbols & Punctuation
    r"＀-￯"            # Halfwidth & Fullwidth Forms
    r"‘-‟"            # Quotation marks
    r"、-。"            # 、。
    r"！？；，" # ！？；，
    r"]"
)

# Decorative / non-linguistic symbols common in noisy web text
_SYMBOL_RE = re.compile(
    r"[#★●■▼▽▲△◆◇○◎※→←↑↓⇒⇐§¶©®™°"
    r"✓✔✗✘✦✧✩✪✫✬✭✮✯✰"
    r"►◄◉◘◙◚◛"
    r"…·•]"  # ellipsis/bullet chars counted as symbols here
)

# Digit characters: ASCII 0-9 and fullwidth ０-９
_DIGIT_RE = re.compile(r"[0-9０-９]")

# Terminal punctuation for "句末标点" check
_TERMINAL_PUNCT_RE = re.compile(
    r'[。！？"…；\.!?;]$'  # ends with any terminal punctuation
)

# Ellipsis at end of line
_ELLIPSIS_END_RE = re.compile(r"(?:\.\.\.|…)\s*$")

# Bullet / list prefix patterns
_BULLET_START_RE = re.compile(r"^\s*(?:[•·\-\*]|\d+\.)\s")

# Chinese function words ("stopwords") — ~30 high-frequency functional tokens
_ZH_STOPWORDS: frozenset[str] = frozenset([
    "的", "了", "是", "在", "和", "不", "有", "我", "他", "这",
    "中", "大", "来", "上", "国", "个", "到", "说", "们", "为",
    "子", "你", "地", "出", "道", "也", "时", "年", "得", "就",
])

# Number of chars in dup-ngram check
_DUP_NGRAM_N: int = 10


# ---------------------------------------------------------------------------
# Per-signal measurement functions
# ---------------------------------------------------------------------------


def _measure_cjk_ratio(text: str) -> float:
    """CJK (+ CJK punctuation) chars / non-whitespace chars."""
    non_ws = sum(1 for ch in text if not ch.isspace())
    if non_ws == 0:
        return 1.0  # empty / all-whitespace: vacuously pass
    return len(_CJK_RE.findall(text)) / non_ws


def _measure_stopword_hits(text: str) -> int:
    """Number of distinct function words present in *text*."""
    return sum(1 for w in _ZH_STOPWORDS if w in text)


def _measure_symbol_ratio(text: str) -> float:
    """Decorative symbol chars / total chars."""
    n = len(text)
    if n == 0:
        return 0.0
    return len(_SYMBOL_RE.findall(text)) / n


def _measure_digit_ratio(text: str) -> float:
    """Digit chars / total chars."""
    n = len(text)
    if n == 0:
        return 0.0
    return len(_DIGIT_RE.findall(text)) / n


def _non_empty_lines(text: str) -> list[str]:
    """Return the list of non-empty lines (strips trailing whitespace)."""
    return [ln.rstrip() for ln in text.split("\n") if ln.strip()]


def _measure_mean_line_len(lines: list[str]) -> float:
    """Mean character count across non-empty lines."""
    if not lines:
        return 0.0
    return sum(len(ln) for ln in lines) / len(lines)


def _measure_ellipsis_line_ratio(lines: list[str]) -> float:
    """Fraction of non-empty lines ending with '…' or '...'."""
    if not lines:
        return 0.0
    return sum(1 for ln in lines if _ELLIPSIS_END_RE.search(ln)) / len(lines)


def _measure_bullet_line_ratio(lines: list[str]) -> float:
    """Fraction of non-empty lines starting with a bullet / ordered-list marker."""
    if not lines:
        return 0.0
    return sum(1 for ln in lines if _BULLET_START_RE.match(ln)) / len(lines)


def _measure_terminal_punct_line_ratio(lines: list[str]) -> float:
    """Fraction of non-empty lines ending with terminal punctuation."""
    if not lines:
        return 0.0
    return sum(1 for ln in lines if _TERMINAL_PUNCT_RE.search(ln)) / len(lines)


def _measure_top_ngram_char_frac(text: str, n: int) -> float:
    """Most-frequent char n-gram's share of total chars (O(n) sliding window)."""
    total = len(text)
    if total < n:
        return 0.0
    counts: Counter = Counter()
    for i in range(total - n + 1):
        counts[text[i : i + n]] += 1
    if not counts:
        return 0.0
    top_count = counts.most_common(1)[0][1]
    # The top n-gram contributes top_count * n chars
    return (top_count * n) / total


def _measure_dup_ngram_char_frac(text: str) -> float:
    """Character coverage of char n-grams (n=10) that appear ≥2 times."""
    n = _DUP_NGRAM_N
    total = len(text)
    if total < n:
        return 0.0

    counts: Counter = Counter()
    for i in range(total - n + 1):
        counts[text[i : i + n]] += 1

    # Sum chars covered by repeated grams (no double-counting: multiply count by n,
    # but cap at total to approximate coverage — RefinedWeb-style heuristic)
    covered = sum(cnt * n for gram, cnt in counts.items() if cnt >= 2)
    return min(covered / total, 1.0)


def _measure_unique_char_ratio(text: str) -> float:
    """Distinct chars / total chars."""
    n = len(text)
    if n == 0:
        return 1.0
    return len(set(text)) / n


# ---------------------------------------------------------------------------
# Rule class
# ---------------------------------------------------------------------------


class QualitySignalsRule(BaseRule):
    """Document-level quality-signal filter (CCNet/Gopher/RefinedWeb, Chinese-adapted).

    Measures a set of quality signals and rejects documents that fail any
    enabled threshold.  All measured values are written to
    ``ctx.quality_signals`` under their signal name, regardless of whether
    the document is ultimately rejected.

    Thresholds are read from ``config.QUALITY_THRESHOLDS``
    (a ``QualityThresholds`` dataclass instance).  Setting a field to ``None``
    disables the corresponding check.

    Empty text (len == 0) passes immediately — upstream rules are responsible
    for rejecting truly empty documents.
    """

    def apply(self, ctx: CleanContext) -> CleanContext:
        text = ctx.text
        thr = C.QUALITY_THRESHOLDS

        # Guard: empty text — let other rules handle it
        if not text:
            return ctx

        lines = _non_empty_lines(text)

        # ------------------------------------------------------------------
        # 1. cjk_ratio — lower bound
        # ------------------------------------------------------------------
        val = _measure_cjk_ratio(text)
        ctx.quality_signals["cjk_ratio"] = val
        if thr.cjk_ratio_min is not None and val < thr.cjk_ratio_min:
            ctx.reject("quality_signals", f"cjk_ratio={val:.3f}")
            return ctx

        # ------------------------------------------------------------------
        # 2. stopword_hits — lower bound (distinct function-word count)
        # ------------------------------------------------------------------
        val_i = _measure_stopword_hits(text)
        ctx.quality_signals["stopword_hits"] = val_i
        if thr.stopword_hits_min is not None and val_i < thr.stopword_hits_min:
            ctx.reject("quality_signals", f"stopword_hits={val_i:.3f}")
            return ctx

        # ------------------------------------------------------------------
        # 3. symbol_ratio — upper bound
        # ------------------------------------------------------------------
        val = _measure_symbol_ratio(text)
        ctx.quality_signals["symbol_ratio"] = val
        if thr.symbol_ratio_max is not None and val > thr.symbol_ratio_max:
            ctx.reject("quality_signals", f"symbol_ratio={val:.3f}")
            return ctx

        # ------------------------------------------------------------------
        # 4. digit_ratio — upper bound
        # ------------------------------------------------------------------
        val = _measure_digit_ratio(text)
        ctx.quality_signals["digit_ratio"] = val
        if thr.digit_ratio_max is not None and val > thr.digit_ratio_max:
            ctx.reject("quality_signals", f"digit_ratio={val:.3f}")
            return ctx

        # ------------------------------------------------------------------
        # 5. mean_line_len — lower bound
        # ------------------------------------------------------------------
        val = _measure_mean_line_len(lines)
        ctx.quality_signals["mean_line_len"] = val
        if thr.mean_line_len_min is not None and lines and val < thr.mean_line_len_min:
            ctx.reject("quality_signals", f"mean_line_len={val:.3f}")
            return ctx

        # ------------------------------------------------------------------
        # 6. ellipsis_line_ratio — upper bound
        # ------------------------------------------------------------------
        val = _measure_ellipsis_line_ratio(lines)
        ctx.quality_signals["ellipsis_line_ratio"] = val
        if thr.ellipsis_line_ratio_max is not None and val > thr.ellipsis_line_ratio_max:
            ctx.reject("quality_signals", f"ellipsis_line_ratio={val:.3f}")
            return ctx

        # ------------------------------------------------------------------
        # 7. bullet_line_ratio — upper bound
        # ------------------------------------------------------------------
        val = _measure_bullet_line_ratio(lines)
        ctx.quality_signals["bullet_line_ratio"] = val
        if thr.bullet_line_ratio_max is not None and val > thr.bullet_line_ratio_max:
            ctx.reject("quality_signals", f"bullet_line_ratio={val:.3f}")
            return ctx

        # ------------------------------------------------------------------
        # 8. terminal_punct_line_ratio — lower bound (only when ≥5 non-empty lines)
        # ------------------------------------------------------------------
        val = _measure_terminal_punct_line_ratio(lines)
        ctx.quality_signals["terminal_punct_line_ratio"] = val
        if (
            thr.terminal_punct_line_ratio_min is not None
            and len(lines) >= 5
            and val < thr.terminal_punct_line_ratio_min
        ):
            ctx.reject("quality_signals", f"terminal_punct_line_ratio={val:.3f}")
            return ctx

        # ------------------------------------------------------------------
        # 9. top_ngram_char_frac for n = 2, 3, 4
        # ------------------------------------------------------------------
        for n, thresh in (
            (2, thr.top_ngram_2_max),
            (3, thr.top_ngram_3_max),
            (4, thr.top_ngram_4_max),
        ):
            val = _measure_top_ngram_char_frac(text, n)
            ctx.quality_signals[f"top_ngram_{n}_char_frac"] = val
            if thresh is not None and val > thresh:
                ctx.reject("quality_signals", f"top_ngram_{n}_char_frac={val:.3f}")
                return ctx

        # ------------------------------------------------------------------
        # 10. dup_ngram_char_frac — upper bound
        # ------------------------------------------------------------------
        val = _measure_dup_ngram_char_frac(text)
        ctx.quality_signals["dup_ngram_char_frac"] = val
        if thr.dup_ngram_char_frac_max is not None and val > thr.dup_ngram_char_frac_max:
            ctx.reject("quality_signals", f"dup_ngram_char_frac={val:.3f}")
            return ctx

        # ------------------------------------------------------------------
        # 11. unique_char_ratio — lower bound (only when len(text) > 2000)
        # ------------------------------------------------------------------
        if len(text) > 2000:
            val = _measure_unique_char_ratio(text)
            ctx.quality_signals["unique_char_ratio"] = val
            if thr.unique_char_ratio_min is not None and val < thr.unique_char_ratio_min:
                ctx.reject("quality_signals", f"unique_char_ratio={val:.3f}")
                return ctx

        return ctx
