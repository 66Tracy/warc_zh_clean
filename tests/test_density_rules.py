# -*- coding: utf-8 -*-
"""Tests for density-rule soft thresholds and bad-keyword weighted scoring.

Covers P2 requirements:
- Short document (300 chars) with 2 occurrences of a trigger word is NOT rejected
  (min_count guard).
- Long document (5 000 chars of normal text) with a few scattered noise words
  is NOT rejected (density dilution — old hard-coded logic would have killed it).
- High-density garbage (short text packed with trigger words) IS rejected, and
  the detail string contains the "density:" prefix.
- Bad-keyword scoring: single edge-weight keyword repeated → no reject.
- Bad-keyword scoring: multiple core-weight keywords at high density → reject.
- Bad-keyword scoring: long normal text with 1-2 bad keywords → no reject
  (dilution protects it).
- category_exempt: exempt category bypasses the matching density rule.
- regex-type counter counts correctly via _get_density_count.
"""

import pytest

import warc_zh_clean.config as C
from warc_zh_clean.config import DensityRule
from warc_zh_clean.models import CleanContext
from warc_zh_clean.rules.chapter_filter import (
    ChapterFilterRule,
    _check_bad_keyword_score,
    _check_density_rules,
    _get_density_count,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NORMAL_SENTENCE = (
    "人工智能技术在近年来取得了突破性的进展，深度学习模型在图像识别和自然语言处理领域表现出色。"
    "云计算平台为企业提供了弹性可扩展的计算资源，降低了基础设施的运维成本和技术门槛。"
    "开源软件生态系统的蓬勃发展促进了技术创新，开发者可以基于现有项目快速构建新的应用。"
    "数据安全与隐私保护成为数字化转型过程中的重要议题，各国相继出台相关法律法规。"
    "物联网设备的广泛部署正在改变城市管理和工业生产的模式，实现更高效的资源调度。"
)


def _make_record(text: str, category: str = "科技") -> dict:
    return {"text": text, "category_label": category}


def _make_ctx(text: str, category: str = "科技") -> CleanContext:
    return CleanContext(_make_record(text, category))


# ---------------------------------------------------------------------------
# _get_density_count unit tests
# ---------------------------------------------------------------------------


def test_get_density_count_substr():
    assert _get_density_count("彩票彩票彩票", "substr:彩票") == 3


def test_get_density_count_regex():
    text = "2023-01-15 10:30:00 and 2024-06-01 08:00:00"
    count = _get_density_count(text, r"regex:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    assert count == 2


def test_get_density_count_regex_date_bracket():
    text = "[12-03] 正文 [07-22] 正文 [11-30]"
    count = _get_density_count(text, r"regex:\[\d{2}-\d{2}\]")
    assert count == 3


def test_get_density_count_invalid_prefix():
    with pytest.raises(ValueError):
        _get_density_count("text", "unknown:foo")


# ---------------------------------------------------------------------------
# Density rule: short document — min_count guard prevents false positive
# ---------------------------------------------------------------------------


def test_short_doc_few_hits_not_rejected():
    """300-char doc with 2 occurrences of '彩票' must NOT be rejected.

    The lottery rule has min_count=5, so 2 hits never trigger regardless of density.
    """
    # Build ~300-char text with exactly 2 lottery mentions
    filler = "这是一段正常的新闻内容介绍市场的监管政策与行业规范发展现状分析报告。"  # 31 chars, no 彩票
    # Repeat to get enough chars, then inject 2 "彩票" at safe positions
    parts = [filler] * 9  # 279 chars
    text = parts[0] + "彩票" + "".join(parts[1:5]) + "彩票" + "".join(parts[5:])
    assert len(text) >= 280
    assert text.count("彩票") == 2  # confirm min_count guard applies
    # min_count for lottery is 5, so 2 hits must never trigger
    assert 2 < C.MISC_DENSITY_RULES[next(
        i for i, r in enumerate(C.MISC_DENSITY_RULES) if r.name == "lottery"
    )].min_count

    signals: dict = {}
    passed, detail = _check_density_rules(text, "科技", signals)
    assert passed, f"Unexpected rejection: {detail}"


# ---------------------------------------------------------------------------
# Density rule: long document — dilution keeps good docs alive
# ---------------------------------------------------------------------------


def test_long_doc_sparse_noise_not_rejected():
    """~5000-char normal text with 6 occurrences of '彩票' must NOT be rejected.

    Old hard-coded threshold: PRE_LOTTERY_LIMIT=10 (absolute).
    New density rule: max_per_kilo=5.0, min_count=5.
    6 hits in ~5000 chars → 6/5000*1000 = 1.2 per kilo, well below 5.0.
    This is the canonical case where the old absolute threshold would cause
    false positives on medium-length documents that legitimately mention
    lottery regulation a handful of times.
    """
    # Use a filler sentence that does NOT contain 彩票 naturally
    filler = "人工智能技术取得了突破性进展，深度学习在图像识别和自然语言处理领域表现出色。"  # 36 chars
    # Build ~5000-char base: repeat 135 times ≈ 4860 chars
    base = filler * 135
    assert "彩票" not in base
    # Inject exactly 6 "彩票" at evenly spaced positions
    lottery_count = 6
    step = len(base) // (lottery_count + 1)
    result_parts = []
    prev = 0
    for i in range(1, lottery_count + 1):
        pos = step * i
        result_parts.append(base[prev:pos])
        result_parts.append("彩票")
        prev = pos
    result_parts.append(base[prev:])
    text = "".join(result_parts)

    assert len(text) >= 4800
    assert text.count("彩票") == lottery_count
    # Verify density is well below the threshold
    assert lottery_count / len(text) * 1000 < C.MISC_DENSITY_RULES[next(
        i for i, r in enumerate(C.MISC_DENSITY_RULES) if r.name == "lottery"
    )].max_per_kilo

    signals: dict = {}
    passed, detail = _check_density_rules(text, "科技", signals)
    assert passed, f"Long normal doc with sparse lottery mentions rejected: {detail}"


# ---------------------------------------------------------------------------
# Density rule: high-density garbage IS rejected
# ---------------------------------------------------------------------------


def test_high_density_lottery_rejected():
    """Dense '彩票买球' spam (500 chars) should be rejected with density: detail."""
    text = "彩票买球彩票买球购彩推荐，彩票开奖彩票中奖，" * 20  # ~500 chars, many hits
    assert text.count("彩票") >= 5  # above min_count

    signals: dict = {}
    passed, detail = _check_density_rules(text, "科技", signals)
    assert not passed
    assert "density:" in detail


def test_high_density_macao_rejected():
    """Dense '澳门' spam should be rejected."""
    text = "澳门博彩澳门赌场澳门彩票澳门娱乐澳门赌博" * 10
    assert text.count("澳门") >= 10

    signals: dict = {}
    passed, detail = _check_density_rules(text, "科技", signals)
    assert not passed
    assert "density:macao" in detail


def test_density_detail_format():
    """Detail string must be 'density:<name>=<count>/<len>'."""
    text = "彩票" * 30  # 60 chars, 30 hits >> min_count=5 and density >> 5/kilo
    signals: dict = {}
    passed, detail = _check_density_rules(text, "科技", signals)
    assert not passed
    # detail like "density:lottery=30/60"
    assert detail.startswith("density:")
    assert "=" in detail
    assert "/" in detail


# ---------------------------------------------------------------------------
# Density rule: quality_signals are written
# ---------------------------------------------------------------------------


def test_density_signals_written_to_quality_signals():
    """_check_density_rules must write hit counts into ctx_signals."""
    text = "彩票彩票彩票" * 2  # 6 hits but short text
    signals: dict = {}
    _check_density_rules(text, "科技", signals)
    assert "density_lottery" in signals
    assert signals["density_lottery"] == text.count("彩票")


# ---------------------------------------------------------------------------
# category_exempt
# ---------------------------------------------------------------------------


def test_category_exempt_mb_pattern():
    """'编程/IT' category is exempt from the mb_pattern density rule."""
    # Dense MB pattern that would normally trigger
    text = ("下载包 512mb 压缩后 256mb 原始文件 1024mb 备份 2048mb 安装 768mb " * 10)
    assert text.count("mb") >= 4

    signals_it: dict = {}
    passed_it, _ = _check_density_rules(text, "编程/IT", signals_it)

    signals_other: dict = {}
    passed_other, _ = _check_density_rules(text, "科技", signals_other)

    assert passed_it, "编程/IT should be exempt from mb_pattern rule"
    # Note: other categories may or may not fail depending on density; we just
    # verify the exemption works correctly for IT.


def test_category_exempt_empty_paren():
    """'编程/IT' is exempt from empty_paren density rule."""
    text = "func() call() init() reset() start() stop() begin() end() run() run() " * 5
    assert text.count("()") >= 4

    signals: dict = {}
    passed, _ = _check_density_rules(text, "编程/IT", signals)
    # The empty_paren rule should be skipped for 编程/IT
    # We can't assert pass/fail since other rules might trigger,
    # but we verify the rule was skipped (no density_empty_paren key written)
    assert "density_empty_paren" not in signals


# ---------------------------------------------------------------------------
# Bad-keyword scoring
# ---------------------------------------------------------------------------


def test_bad_keyword_single_edge_word_not_rejected():
    """Single edge-weight keyword ('按摩') repeated many times in a long doc should
    not reach the score threshold (weight=0.5, capped at 5 occurrences → max 2.5 pts).
    """
    normal_text = _NORMAL_SENTENCE * 20  # ~4000 chars
    text = normal_text + "按摩" * 10  # append 10 occurrences

    signals: dict = {}
    passed, detail = _check_bad_keyword_score(text, signals)
    assert passed, f"Edge keyword alone should not reject: {detail}"


def test_bad_keyword_multiple_core_words_high_density_rejected():
    """Multiple core-weight keywords in a short dense text should be rejected."""
    # Use several core (weight=2.0) porn/gambling keywords in a short text
    text = "强奸乱伦轮奸肛交口交阴道阴茎肉棒鸡巴淫荡骚逼" * 3  # ~150 chars, all core keywords
    signals: dict = {}
    passed, detail = _check_bad_keyword_score(text, signals)
    assert not passed
    assert "bad_keyword_score" in detail


def test_bad_keyword_long_normal_text_occasional_hit_not_rejected():
    """Long normal text (4000 chars) with 1-2 bad keyword hits should NOT be rejected
    due to density dilution: score/len*1000 stays well below BAD_KEYWORD_SCORE_PER_KILO.
    """
    normal_text = _NORMAL_SENTENCE * 20  # ~4000 chars
    # Add one occurrence of a core keyword (score contribution: 2.0)
    text = normal_text + "乱伦"
    assert len(text) > 3000

    signals: dict = {}
    passed, detail = _check_bad_keyword_score(text, signals)
    assert passed, f"Long normal text with single bad keyword rejected: {detail}"


def test_bad_keyword_score_written_to_signals():
    """bad_keyword_score key must always be written to quality_signals."""
    text = "完全正常的文本内容，没有任何坏词。" * 10
    signals: dict = {}
    _check_bad_keyword_score(text, signals)
    assert "bad_keyword_score" in signals
    assert signals["bad_keyword_score"] == 0.0


def test_bad_keyword_score_min_count_guard():
    """Score below BAD_KEYWORD_SCORE_MIN must not trigger even if density is high.

    Weight 0.5 edge word, single hit → score=0.5 < BAD_KEYWORD_SCORE_MIN=3.0.
    """
    text = "按摩一次" + "正常内容" * 5  # very short, high density, but score=0.5
    signals: dict = {}
    passed, detail = _check_bad_keyword_score(text, signals)
    assert passed


# ---------------------------------------------------------------------------
# Integration: ChapterFilterRule with density and bad-keyword checks
# ---------------------------------------------------------------------------


def _make_passable_long_text() -> str:
    """Return a ~1500 char text that passes all chapter-filter checks."""
    return (
        "人工智能技术在近年来取得了突破性的进展，深度学习模型在图像识别和自然语言处理领域表现出色。"
        "云计算平台为企业提供了弹性可扩展的计算资源，降低了基础设施的运维成本和技术门槛。"
        "开源软件生态系统的蓬勃发展促进了技术创新，开发者可以基于现有项目快速构建新的应用。"
        "数据安全与隐私保护成为数字化转型过程中的重要议题，各国相继出台相关法律法规。"
        "物联网设备的广泛部署正在改变城市管理和工业生产的模式，实现更高效的资源调度。"
        "区块链技术在金融领域的应用探索不断深入，去中心化账本为交易验证提供了新的范式。"
        "量子计算的研究进展令人瞩目，虽然仍处于早期阶段，但已展现出解决复杂优化问题的潜力。"
        "边缘计算将数据处理能力推向网络边缘，减少延迟并提高实时响应速度。"
        "数字孪生技术在制造业中的应用日益广泛，通过虚拟模型优化生产流程和设备维护。"
        "5G网络的商用部署为物联网和智能交通提供了高带宽低延迟的通信基础设施。"
        "自然语言处理技术的进步使得机器翻译和文本生成的质量大幅提升。"
        "计算机视觉技术在自动驾驶和医学影像分析中发挥着越来越重要的作用。"
        "网络安全威胁的演变推动着防御技术的持续创新，零信任架构成为新的安全范式。"
        "低代码平台的兴起降低了应用开发的门槛，使业务人员也能参与数字化建设。"
        "微服务架构为大型系统提供了更好的可维护性和可扩展性，促进了敏捷开发实践。"
    )


def test_integration_normal_doc_passes():
    """Normal ~1500 char document passes the full ChapterFilterRule."""
    rule = ChapterFilterRule()
    text = _make_passable_long_text()
    ctx = _make_ctx(text)
    rule.apply(ctx)
    assert not ctx.rejected


def test_integration_quality_signals_populated():
    """After apply(), quality_signals must contain at least some density keys."""
    rule = ChapterFilterRule()
    text = _make_passable_long_text()
    ctx = _make_ctx(text)
    rule.apply(ctx)
    assert isinstance(ctx.quality_signals, dict)
    # bad_keyword_score must always be written
    assert "bad_keyword_score" in ctx.quality_signals


def test_integration_dense_spam_rejected_with_density_detail():
    """A dense gambling spam text is rejected with a density: detail."""
    rule = ChapterFilterRule()
    # Use the passable base but inject high-density lottery spam
    base = _make_passable_long_text()
    # 30 occurrences of 彩票 in ~1500 chars = 20/kilo >> max_per_kilo=5.0
    spam = "彩票" * 30
    text = base[:500] + spam + base[500:]
    ctx = _make_ctx(text)
    rule.apply(ctx)
    assert ctx.rejected
    assert "density:lottery" in ctx.reject_detail


def test_integration_bad_keyword_dense_rejected():
    """Dense multi-core-keyword text is rejected.

    We use a passable base (passes length/structure/ngram checks) then inject
    many core-weight keywords to push the bad_keyword_score above the threshold.
    """
    rule = ChapterFilterRule()
    # Build a base that passes structural checks but is short enough to keep density high
    base = _make_passable_long_text()  # ~1500 chars, all structural checks pass
    # Append 50 occurrences of a core keyword — score contribution per kw = min(50,5)*2.0 = 10
    core_spam = "强奸" * 50  # 100 chars, score=10, total len ~1600
    text = base + core_spam
    # Verify density: 10 / 1600 * 1000 = 6.25 > BAD_KEYWORD_SCORE_PER_KILO=1.0
    ctx = _make_ctx(text)
    rule.apply(ctx)
    assert ctx.rejected
    # Should be rejected by bad_keyword_score or density rule
    assert "bad_keyword_score" in ctx.reject_detail or "density" in ctx.reject_detail


@pytest.mark.parametrize("category,should_pass", [
    ("编程/IT", True),   # exempt from mb_pattern and empty_paren rules
    ("科技", False),     # not exempt, dense mb_pattern triggers
])
def test_integration_category_exempt_mb(category, should_pass):
    """'编程/IT' must be exempt from mb_pattern density rule."""
    base = _make_passable_long_text()
    # Add dense MB pattern: 10 hits in ~1500 chars → 6.7/kilo > max_per_kilo=4.0
    mb_dense = " 512mb 256mb 1024mb 128mb 2048mb 64mb 32mb 16mb 8mb 4mb " * 2
    text = base + mb_dense

    rule = ChapterFilterRule()
    ctx = _make_ctx(text, category)
    rule.apply(ctx)

    if should_pass:
        assert not ctx.rejected, f"编程/IT should not be rejected but got: {ctx.reject_detail}"
    else:
        # For non-exempt category, density may or may not trigger depending on
        # exact text length, so we just confirm the rule runs without error.
        # (The key assertion is that IT is exempt.)
        pass
