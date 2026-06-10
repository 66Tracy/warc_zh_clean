# -*- coding: utf-8 -*-
"""Unit tests for PostLengthFilterRule and RatioFilterRule."""

from warc_zh_clean.rules.post_filter import (
    PostLengthFilterRule,
    RatioFilterRule,
    _post_filtering,
)
from warc_zh_clean.models import CleanContext


def test_post_filtering_too_short():
    text = "短文本"
    passed, detail = _post_filtering(text)
    assert passed is False
    assert detail == "post_text_too_short"


def test_post_filtering_normal_text():
    text = (
        "经过行级清洗后保留的正文段落，包含足够的文字内容来通过长度检查。"
        "每一个段落都有不同的内容，确保不会被重复检测过滤掉。"
        "这些内容涵盖了多个方面，从技术发展到社会变迁都有涉及。"
        "文本的质量较高，不包含广告、导航或其他模板噪声。"
        "经过处理后的文本结构清晰，语义连贯，适合作为训练数据。"
        "清洗过程包括敏感信息替换、行级噪声删除和文档级质量过滤。"
        "最终的输出数据将用于大规模语言模型的预训练语料构建。"
        "我们采用多阶段清洗策略，每个阶段都有独立的过滤和转换规则。"
        "数据质量是训练效果的基础保障，严格清洗流程不可省略。"
        "通过对清洗前后文本长度比的计算，我们能够有效识别过度截断的情况。"
        "在清洗流水线中，预过滤阶段负责快速排除明显低质量的文档。"
        "行级规则针对广告、导航、版权声明等模板噪声进行精准删除。"
        "后过滤阶段则从文档整体维度评估文本质量，确保输出数据的可靠性。"
        "整个流程设计遵循召回优先的原则，避免误杀有价值的正常文本。"
        "这套清洗方案已经在多个中文数据集上验证了其有效性和稳定性。"
        "以上内容经过严格的质量控制和多轮清洗。"
    )
    passed, detail = _post_filtering(text)
    assert passed is True


def test_post_length_filter_rejects_short():
    rule = PostLengthFilterRule()
    ctx = CleanContext({"text": "短文本"})
    ctx = rule.apply(ctx)
    assert ctx.rejected is True
    assert ctx.reject_reason == "post_filter"


def test_post_length_filter_accepts_normal():
    rule = PostLengthFilterRule()
    text = (
        "经过行级清洗后保留的正文段落，包含足够的文字内容来通过长度检查。"
        "每一个段落都有不同的内容，确保不会被重复检测过滤掉。"
        "这些内容涵盖了多个方面，从技术发展到社会变迁都有涉及。"
        "文本的质量较高，不包含广告、导航或其他模板噪声。"
        "经过处理后的文本结构清晰，语义连贯，适合作为训练数据。"
        "清洗过程包括敏感信息替换、行级噪声删除和文档级质量过滤。"
        "最终的输出数据将用于大规模语言模型的预训练语料构建。"
        "我们采用多阶段清洗策略，每个阶段都有独立的过滤和转换规则。"
        "数据质量是训练效果的基础保障，严格清洗流程不可省略。"
        "通过对清洗前后文本长度比的计算，我们能够有效识别过度截断的情况。"
        "在清洗流水线中，预过滤阶段负责快速排除明显低质量的文档。"
        "行级规则针对广告、导航、版权声明等模板噪声进行精准删除。"
        "后过滤阶段则从文档整体维度评估文本质量，确保输出数据的可靠性。"
        "整个流程设计遵循召回优先的原则，避免误杀有价值的正常文本。"
        "这套清洗方案已经在多个中文数据集上验证了其有效性和稳定性。"
        "以上内容经过严格的质量控制和多轮清洗。"
    )
    ctx = CleanContext({"text": text})
    ctx = rule.apply(ctx)
    assert not ctx.rejected


def test_ratio_filter_rejects_low_ratio():
    rule = RatioFilterRule()
    ctx = CleanContext({"text": "短文本"})
    ctx.text_len = 1000  # Pre-cleaning text was long
    ctx = rule.apply(ctx)
    assert ctx.rejected is True
    assert ctx.reject_reason == "ratio_filter"


def test_ratio_filter_accepts_normal():
    rule = RatioFilterRule()
    ctx = CleanContext({"text": "这是一段正常的文本内容"})
    ctx.text_len = 20  # Similar length before and after
    ctx = rule.apply(ctx)
    assert not ctx.rejected


def test_ratio_filter_zero_text_len():
    rule = RatioFilterRule()
    ctx = CleanContext({"text": "some text"})
    ctx.text_len = 0
    ctx = rule.apply(ctx)
    assert ctx.rejected is True
    assert ctx.reject_detail == "text_len_is_zero"