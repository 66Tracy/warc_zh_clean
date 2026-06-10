# -*- coding: utf-8 -*-
"""Unit tests for ChapterFilterRule."""

from warc_zh_clean.rules.chapter_filter import (
    ChapterFilterRule,
    _check_length,
    _check_category,
    _check_zlib,
    _check_basic_quality,
    _check_duplicate_fraction,
    _has_frequent_ngram,
)
from warc_zh_clean.models import CleanContext


def test_check_length_too_short():
    passed, detail = _check_length("太短的文本")
    assert passed is False
    assert detail == "text_too_short"


def test_check_length_ok():
    text = "这是一段足够长的文本内容，" * 30
    passed, detail = _check_length(text)
    assert passed is True


def test_check_category_blocked():
    passed, detail = _check_category("赌博/色情/非法")
    assert passed is False
    assert detail == "blocked_category"


def test_check_category_ok():
    passed, detail = _check_category("科技")
    assert passed is True


def test_check_basic_quality_normal():
    text = "这是一段正常的文档内容。\n第二行有更多内容。\n第三行继续。"
    passed, detail = _check_basic_quality(text)
    assert passed is True


def test_check_basic_quality_high_symbol_rate():
    text = "!@#$%^&*()_+" * 50
    passed, detail = _check_basic_quality(text)
    assert passed is False
    assert detail == "non_cjk_ratio_high"


def test_check_duplicate_fraction_normal():
    text = "第一行内容\n第二行内容\n第三行内容\n第四行内容\n第五行内容"
    passed, detail = _check_duplicate_fraction(text)
    assert passed is True


def test_check_duplicate_fraction_duplicate_lines():
    line = "重复的行内容"
    text = "\n".join([line] * 50)
    passed, detail = _check_duplicate_fraction(text)
    assert passed is False


def test_has_frequent_ngram_below():
    tokens = list("abcdefghij")
    assert _has_frequent_ngram(tokens, 3, 5) is False


def test_has_frequent_ngram_above():
    tokens = list("abcabcabcabcabc")
    assert _has_frequent_ngram(tokens, 3, 3) is True


def test_chapter_filter_rejects_short():
    rule = ChapterFilterRule()
    ctx = CleanContext({"text": "太短的文本", "category_label": "科技"})
    ctx = rule.apply(ctx)
    assert ctx.rejected is True
    assert ctx.reject_reason == "filter_rules_2"


def test_chapter_filter_rejects_bad_category():
    rule = ChapterFilterRule()
    long_text = "这是一段足够长的文本内容，" * 30
    ctx = CleanContext({"text": long_text, "category_label": "赌博/色情/非法"})
    ctx = rule.apply(ctx)
    assert ctx.rejected is True


def test_chapter_filter_accepts_normal():
    rule = ChapterFilterRule()
    text = (
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
    ctx = CleanContext({"text": text, "category_label": "科技"})
    ctx = rule.apply(ctx)
    assert not ctx.rejected