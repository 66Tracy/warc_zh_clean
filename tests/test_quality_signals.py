# -*- coding: utf-8 -*-
"""Tests for QualitySignalsRule (P4).

Coverage:
- Each of the 11 signals: ≥1 pass + ≥1 reject case, key signals have boundary cases.
- Threshold=None disables individual checks.
- A clean real-style Chinese article (400+ chars, all signals pass) used for calibration.
- Empty text guard.
"""

import pytest

from warc_zh_clean.models import CleanContext
from warc_zh_clean.rules.quality_signals import (
    QualitySignalsRule,
    _measure_cjk_ratio,
    _measure_stopword_hits,
    _measure_symbol_ratio,
    _measure_digit_ratio,
    _measure_mean_line_len,
    _measure_ellipsis_line_ratio,
    _measure_bullet_line_ratio,
    _measure_terminal_punct_line_ratio,
    _measure_top_ngram_char_frac,
    _measure_dup_ngram_char_frac,
    _measure_unique_char_ratio,
    _non_empty_lines,
)
from warc_zh_clean.config import QualityThresholds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(text: str, category: str = "科技") -> CleanContext:
    return CleanContext({"text": text, "category_label": category})


def _apply_with_thr(text: str, thr: QualityThresholds) -> CleanContext:
    """Apply QualitySignalsRule with a custom threshold set."""
    import warc_zh_clean.config as C
    old = C.QUALITY_THRESHOLDS
    C.QUALITY_THRESHOLDS = thr
    try:
        rule = QualitySignalsRule()
        ctx = _make_ctx(text)
        return rule.apply(ctx)
    finally:
        C.QUALITY_THRESHOLDS = old


# ---------------------------------------------------------------------------
# Shared diverse Chinese text (passes all default thresholds)
# ---------------------------------------------------------------------------

# 200+ chars, many different sentences to avoid high n-gram repetition
_DIVERSE_CHINESE = (
    "人工智能技术在近年来取得了突破性的进展，深度学习模型在图像识别和自然语言处理领域表现出色。"
    "云计算平台为企业提供了弹性可扩展的计算资源，降低了基础设施的运维成本和技术门槛。"
    "开源软件生态系统的蓬勃发展促进了技术创新，开发者可以基于现有项目快速构建新的应用。"
    "数据安全与隐私保护成为数字化转型过程中的重要议题，各国相继出台相关法律法规。"
    "物联网设备的广泛部署正在改变城市管理和工业生产的模式，实现更高效的资源调度。"
)

# Real-style Chinese article, all signals should pass the default thresholds.
# If this text fails a default threshold, calibrate the threshold, not the text.
_REAL_ARTICLE = (
    "中国探月工程嫦娥五号任务于2020年11月24日成功发射，探测器经过约23天的飞行后，"
    "在月球正面的吕姆克山脉附近实施软着陆，并完成了钻取和表取两种方式的月壤采集工作。"
    "此次任务共采集月球样本约1.731千克，于2020年12月17日成功返回地球，"
    "降落在内蒙古四子王旗预定区域。\n"
    "这是中国首次实现地外天体采样返回，也是人类时隔44年再次带回月球样品。"
    "科学家对嫦娥五号带回的月壤样品进行了系统分析，发现其年龄约为20亿年，"
    "比阿波罗任务采集的样品年轻约10亿至20亿年，为研究月球火山活动的持续时间提供了新证据。\n"
    "嫦娥五号任务的成功标志着中国探月工程三步走战略绕落回的圆满完成，"
    "为后续载人登月和月球科研站建设奠定了重要基础。"
    "国际社会对此次任务给予高度评价，多个国家和国际组织表示祝贺。\n"
    "在技术层面，此次任务攻克了月面起飞、月球轨道交会对接等多项关键技术，"
    "标志着中国在深空探测领域达到了国际先进水平。"
    "未来，中国计划实施嫦娥六号、七号、八号任务，"
    "进一步深化对月球南极区域的探测与研究，并为建立国际月球科研站做好前期准备工作。"
    "科研人员表示，这批珍贵的月球样品将在地质学、行星科学和宇宙化学等多个领域带来重要发现。\n"
    "探月工程的每一次成功都凝聚了无数科研人员的心血与智慧，是中国航天事业蓬勃发展的有力证明。"
    "随着更多深空探测任务的推进，人类对宇宙的认识将不断深化，为未来的星际探索奠定坚实基础。"
)


# ===========================================================================
# 1. Empty text guard
# ===========================================================================

class TestEmptyTextGuard:
    def test_empty_text_passes_immediately(self):
        rule = QualitySignalsRule()
        ctx = _make_ctx("")
        ctx = rule.apply(ctx)
        assert not ctx.rejected

    def test_empty_text_no_signals_written(self):
        rule = QualitySignalsRule()
        ctx = _make_ctx("")
        ctx = rule.apply(ctx)
        assert ctx.quality_signals == {}


# ===========================================================================
# 2. cjk_ratio
# ===========================================================================

class TestCjkRatio:
    def test_pass_high_cjk(self):
        # Diverse Chinese text → cjk_ratio close to 1.0
        ctx = _apply_with_thr(_DIVERSE_CHINESE, QualityThresholds(cjk_ratio_min=0.30))
        assert not ctx.rejected
        assert ctx.quality_signals["cjk_ratio"] > 0.30

    def test_reject_low_cjk(self):
        # All ASCII — cjk_ratio = 0
        text = "hello world this is pure english text without any chinese characters here " * 5
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=0.30,
                stopword_hits_min=None,
            ),
        )
        assert ctx.rejected
        assert ctx.reject_detail.startswith("cjk_ratio=")

    def test_measure_cjk_ratio_pure_chinese(self):
        text = "你好世界"  # 4 CJK chars, 0 non-CJK non-whitespace
        assert _measure_cjk_ratio(text) == 1.0

    def test_measure_cjk_ratio_mixed(self):
        # 3 CJK + 7 ASCII = 30%
        text = "的的的abcdefg"
        ratio = _measure_cjk_ratio(text)
        assert abs(ratio - 0.30) < 0.01

    def test_disabled_when_none(self):
        text = "pure english only no chinese" * 10
        ctx = _apply_with_thr(
            text,
            QualityThresholds(cjk_ratio_min=None, stopword_hits_min=None),
        )
        if ctx.rejected:
            assert "cjk_ratio" not in ctx.reject_detail


# ===========================================================================
# 3. stopword_hits
# ===========================================================================

class TestStopwordHits:
    def test_pass_many_stopwords(self):
        # Diverse Chinese has many function words
        hits = _measure_stopword_hits(_DIVERSE_CHINESE)
        assert hits >= 3

    def test_reject_no_stopwords(self):
        # Pure digits — no function words
        text = "12345 67890 11223 44556 " * 10
        ctx = _apply_with_thr(
            text,
            QualityThresholds(cjk_ratio_min=None, stopword_hits_min=3),
        )
        assert ctx.rejected
        assert "stopword_hits" in ctx.reject_detail

    def test_boundary_exactly_3_hits(self):
        # Exactly 3 distinct function words present
        text = "的了是" + "a" * 200
        hits = _measure_stopword_hits(text)
        assert hits == 3

    def test_disabled_when_none(self):
        text = "12345 67890" * 20
        ctx = _apply_with_thr(
            text,
            QualityThresholds(cjk_ratio_min=None, stopword_hits_min=None),
        )
        if ctx.rejected:
            assert "stopword_hits" not in ctx.reject_detail


# ===========================================================================
# 4. symbol_ratio
# ===========================================================================

class TestSymbolRatio:
    def test_pass_no_symbols(self):
        # Diverse Chinese has no decorative symbols
        ctx = _apply_with_thr(_DIVERSE_CHINESE, QualityThresholds(symbol_ratio_max=0.10))
        assert not ctx.rejected
        assert ctx.quality_signals["symbol_ratio"] < 0.10

    def test_reject_high_symbols(self):
        # > 10% symbols: 12 symbols + 80 plain chars = ~13%
        text = "★●■▼★●■▼★●■▼" + "a" * 80
        assert _measure_symbol_ratio(text) > 0.10
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None, symbol_ratio_max=0.10
            ),
        )
        assert ctx.rejected
        assert "symbol_ratio" in ctx.reject_detail

    def test_measure_symbol_ratio_pure_symbols(self):
        text = "★●■▼" * 10
        ratio = _measure_symbol_ratio(text)
        assert ratio == 1.0

    def test_disabled_when_none(self):
        text = "★★★★★★★★★★★★★★★★★★★★" * 5
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None, symbol_ratio_max=None
            ),
        )
        if ctx.rejected:
            assert "symbol_ratio" not in ctx.reject_detail


# ===========================================================================
# 5. digit_ratio
# ===========================================================================

class TestDigitRatio:
    def test_pass_few_digits(self):
        # Diverse Chinese has few digits
        assert _measure_digit_ratio(_DIVERSE_CHINESE) < 0.30

    def test_reject_high_digits(self):
        # > 30% digits: 100 digits / 120 total = 83%
        text = "1234567890" * 10 + "ab" * 10
        assert _measure_digit_ratio(text) > 0.30
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=0.30,
            ),
        )
        assert ctx.rejected
        assert "digit_ratio" in ctx.reject_detail

    def test_disabled_when_none(self):
        text = "1234567890" * 20
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
            ),
        )
        if ctx.rejected:
            assert "digit_ratio" not in ctx.reject_detail


# ===========================================================================
# 6. mean_line_len
# ===========================================================================

class TestMeanLineLen:
    def test_pass_long_lines(self):
        lines = _non_empty_lines(_DIVERSE_CHINESE)
        assert _measure_mean_line_len(lines) >= 10

    def test_reject_short_lines(self):
        # Each line is only 3 chars → mean = 3 < 10
        text = "\n".join(["你好啊"] * 10)
        lines = _non_empty_lines(text)
        assert _measure_mean_line_len(lines) < 10
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=10.0,
            ),
        )
        assert ctx.rejected
        assert "mean_line_len" in ctx.reject_detail

    def test_disabled_when_none(self):
        text = "\n".join(["a"] * 20)
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None,
            ),
        )
        if ctx.rejected:
            assert "mean_line_len" not in ctx.reject_detail


# ===========================================================================
# 7. ellipsis_line_ratio
# ===========================================================================

class TestEllipsisLineRatio:
    def test_pass_few_ellipsis(self):
        text = "第一行正常内容。\n第二行也是正常的。\n第三行...\n第四行继续。\n第五行结束。"
        lines = _non_empty_lines(text)
        ratio = _measure_ellipsis_line_ratio(lines)
        assert ratio <= 0.30

    def test_reject_many_ellipsis(self):
        # 4/5 lines end with ellipsis = 80% > 30%
        text = "行一...\n行二...\n行三...\n行四...\n行五正常。"
        lines = _non_empty_lines(text)
        assert _measure_ellipsis_line_ratio(lines) > 0.30
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=0.30,
            ),
        )
        assert ctx.rejected
        assert "ellipsis_line_ratio" in ctx.reject_detail

    def test_disabled_when_none(self):
        text = "...\n...\n...\n...\n..."
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
            ),
        )
        if ctx.rejected:
            assert "ellipsis_line_ratio" not in ctx.reject_detail


# ===========================================================================
# 8. bullet_line_ratio
# ===========================================================================

class TestBulletLineRatio:
    def test_pass_few_bullets(self):
        text = "正常行内容。\n正常行继续。\n• 项目一\n正文段落。\n• 项目二"
        lines = _non_empty_lines(text)
        assert _measure_bullet_line_ratio(lines) < 0.90

    def test_reject_all_bullets(self):
        text = "\n".join(["• 条目内容"] * 10)
        lines = _non_empty_lines(text)
        assert _measure_bullet_line_ratio(lines) > 0.90
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=0.90,
            ),
        )
        assert ctx.rejected
        assert "bullet_line_ratio" in ctx.reject_detail

    def test_disabled_when_none(self):
        text = "\n".join(["• 条目"] * 20)
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None,
            ),
        )
        if ctx.rejected:
            assert "bullet_line_ratio" not in ctx.reject_detail


# ===========================================================================
# 9. terminal_punct_line_ratio
# ===========================================================================

class TestTerminalPunctLineRatio:
    def test_pass_high_terminal_punct(self):
        lines = [
            "这是第一句话。",
            "这是第二句话！",
            "这是第三句话？",
            "这是第四句话。",
            "这是第五句话！",
        ]
        text = "\n".join(lines)
        lns = _non_empty_lines(text)
        ratio = _measure_terminal_punct_line_ratio(lns)
        assert ratio >= 0.20

    def test_reject_low_terminal_punct(self):
        # Navigation-style lines with no terminal punctuation
        lines = ["首页", "关于我们", "联系方式", "产品服务", "新闻中心", "下载中心"]
        text = "\n".join(lines)
        lns = _non_empty_lines(text)
        ratio = _measure_terminal_punct_line_ratio(lns)
        assert ratio < 0.20
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None,
                terminal_punct_line_ratio_min=0.20,
            ),
        )
        assert ctx.rejected
        assert "terminal_punct_line_ratio" in ctx.reject_detail

    def test_not_checked_below_5_lines(self):
        # Only 4 lines: check must be skipped
        text = "首页\n关于我们\n联系方式\n产品服务"
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None,
                terminal_punct_line_ratio_min=0.20,
            ),
        )
        if ctx.rejected:
            assert "terminal_punct" not in ctx.reject_detail

    def test_disabled_when_none(self):
        text = "\n".join(["abc def ghi"] * 10)
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None,
                terminal_punct_line_ratio_min=None,
            ),
        )
        if ctx.rejected:
            assert "terminal_punct" not in ctx.reject_detail


# ===========================================================================
# 10. top_ngram_char_frac (n=2, 3, 4)
# ===========================================================================

class TestTopNgramCharFrac:
    def test_pass_diverse_text(self):
        for n, thr_val in [(2, 0.20), (3, 0.18), (4, 0.16)]:
            val = _measure_top_ngram_char_frac(_DIVERSE_CHINESE, n)
            assert val < thr_val, f"n={n}: {val:.3f} should be < {thr_val}"

    def test_reject_repetitive_2gram(self):
        # "哈哈" repeated: top 2-gram covers ~100% of chars
        text = "哈哈" * 100
        val = _measure_top_ngram_char_frac(text, 2)
        assert val > 0.20
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None, terminal_punct_line_ratio_min=None,
                top_ngram_2_max=0.20,
            ),
        )
        assert ctx.rejected
        assert "top_ngram_2" in ctx.reject_detail

    def test_reject_repetitive_3gram(self):
        text = "abc" * 100
        val = _measure_top_ngram_char_frac(text, 3)
        assert val > 0.18
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None, terminal_punct_line_ratio_min=None,
                top_ngram_2_max=None, top_ngram_3_max=0.18,
            ),
        )
        assert ctx.rejected
        assert "top_ngram_3" in ctx.reject_detail

    def test_reject_repetitive_4gram(self):
        text = "abcd" * 100
        val = _measure_top_ngram_char_frac(text, 4)
        assert val > 0.16
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None, terminal_punct_line_ratio_min=None,
                top_ngram_2_max=None, top_ngram_3_max=None, top_ngram_4_max=0.16,
            ),
        )
        assert ctx.rejected
        assert "top_ngram_4" in ctx.reject_detail

    def test_disabled_when_all_none(self):
        text = "哈哈哈哈哈哈哈哈哈哈" * 50
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None, terminal_punct_line_ratio_min=None,
                top_ngram_2_max=None, top_ngram_3_max=None, top_ngram_4_max=None,
            ),
        )
        if ctx.rejected:
            assert "top_ngram" not in ctx.reject_detail


# ===========================================================================
# 11. dup_ngram_char_frac
# ===========================================================================

class TestDupNgramCharFrac:
    def test_pass_no_repetition(self):
        # Classic Chinese text — no repeated 10-grams
        text = "天地玄黄宇宙洪荒日月盈昃辰宿列张寒来暑往秋收冬藏闰余成岁律吕调阳云腾致雨露结为霜"
        val = _measure_dup_ngram_char_frac(text)
        assert val <= 0.15

    def test_reject_high_dup_ngram(self):
        # 10-char phrase repeated many times
        phrase10 = "这段话在不断重复着！"  # 9 chars; make it 10:
        phrase10 = "这段话真的一直在重复！"  # 10 CJK + 1 punctuation = 11, try simpler:
        phrase10 = "1234567890"  # 10 ASCII chars
        text = phrase10 * 50  # 500 chars, top 10-gram covers almost all
        val = _measure_dup_ngram_char_frac(text)
        assert val > 0.15
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None, terminal_punct_line_ratio_min=None,
                top_ngram_2_max=None, top_ngram_3_max=None, top_ngram_4_max=None,
                dup_ngram_char_frac_max=0.15,
            ),
        )
        assert ctx.rejected
        assert "dup_ngram_char_frac" in ctx.reject_detail

    def test_disabled_when_none(self):
        text = "1234567890" * 50
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None, terminal_punct_line_ratio_min=None,
                top_ngram_2_max=None, top_ngram_3_max=None, top_ngram_4_max=None,
                dup_ngram_char_frac_max=None,
            ),
        )
        if ctx.rejected:
            assert "dup_ngram" not in ctx.reject_detail


# ===========================================================================
# 12. unique_char_ratio (only checked when len(text) > 2000)
# ===========================================================================

class TestUniqueCharRatio:
    def test_pass_diverse_chars_long_text(self):
        # Build a >2000-char text with many unique chars
        text = _DIVERSE_CHINESE * 10  # 202 * 10 = 2020 chars
        assert len(text) > 2000
        val = _measure_unique_char_ratio(text)
        assert val >= 0.03

    def test_reject_single_char_long_text(self):
        text = "啊" * 3000
        val = _measure_unique_char_ratio(text)
        assert val < 0.03
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None, terminal_punct_line_ratio_min=None,
                top_ngram_2_max=None, top_ngram_3_max=None, top_ngram_4_max=None,
                dup_ngram_char_frac_max=None, unique_char_ratio_min=0.03,
            ),
        )
        assert ctx.rejected
        assert "unique_char_ratio" in ctx.reject_detail

    def test_not_checked_for_short_text(self):
        # ≤2000 chars: check skipped even if ratio would fail
        text = "啊" * 200
        assert len(text) <= 2000
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None, terminal_punct_line_ratio_min=None,
                top_ngram_2_max=None, top_ngram_3_max=None, top_ngram_4_max=None,
                dup_ngram_char_frac_max=None, unique_char_ratio_min=0.03,
            ),
        )
        assert not ctx.rejected

    def test_disabled_when_none(self):
        text = "啊" * 3000
        ctx = _apply_with_thr(
            text,
            QualityThresholds(
                cjk_ratio_min=None, stopword_hits_min=None,
                symbol_ratio_max=None, digit_ratio_max=None,
                mean_line_len_min=None, ellipsis_line_ratio_max=None,
                bullet_line_ratio_max=None, terminal_punct_line_ratio_min=None,
                top_ngram_2_max=None, top_ngram_3_max=None, top_ngram_4_max=None,
                dup_ngram_char_frac_max=None, unique_char_ratio_min=None,
            ),
        )
        assert not ctx.rejected


# ===========================================================================
# 13. Quality signals written to ctx.quality_signals
# ===========================================================================

class TestSignalsWrittenToContext:
    def test_all_signals_written_for_normal_text(self):
        rule = QualitySignalsRule()
        ctx = _make_ctx(_DIVERSE_CHINESE)
        rule.apply(ctx)
        expected_keys = {
            "cjk_ratio", "stopword_hits", "symbol_ratio", "digit_ratio",
            "mean_line_len", "ellipsis_line_ratio", "bullet_line_ratio",
            "terminal_punct_line_ratio",
            "top_ngram_2_char_frac", "top_ngram_3_char_frac", "top_ngram_4_char_frac",
            "dup_ngram_char_frac",
        }
        for key in expected_keys:
            assert key in ctx.quality_signals, f"Missing signal: {key}"


# ===========================================================================
# 14. Real-style 400+ char Chinese article — must pass all default thresholds
# ===========================================================================
#
# This test calibrates the default thresholds.  If it fails, adjust the
# default QualityThresholds values in config.py, NOT this text.

class TestRealArticlePassesAllDefaults:
    def test_real_article_minimum_length(self):
        assert len(_REAL_ARTICLE) >= 400, (
            f"Article is {len(_REAL_ARTICLE)} chars, extend _REAL_ARTICLE"
        )

    def test_real_article_passes_all_default_thresholds(self):
        """Clean Chinese news article must pass all default thresholds."""
        rule = QualitySignalsRule()
        ctx = _make_ctx(_REAL_ARTICLE)
        ctx = rule.apply(ctx)
        assert not ctx.rejected, (
            f"Real article rejected: {ctx.reject_detail!r}. "
            "Calibrate the default threshold, not the text."
        )

    def test_real_article_cjk_ratio_above_min(self):
        val = _measure_cjk_ratio(_REAL_ARTICLE)
        assert val >= 0.30, f"cjk_ratio={val:.3f}"

    def test_real_article_stopwords_above_min(self):
        assert _measure_stopword_hits(_REAL_ARTICLE) >= 3

    def test_real_article_symbol_ratio_below_max(self):
        assert _measure_symbol_ratio(_REAL_ARTICLE) <= 0.10

    def test_real_article_digit_ratio_below_max(self):
        assert _measure_digit_ratio(_REAL_ARTICLE) <= 0.30

    def test_real_article_mean_line_len_above_min(self):
        lines = _non_empty_lines(_REAL_ARTICLE)
        assert _measure_mean_line_len(lines) >= 10.0
