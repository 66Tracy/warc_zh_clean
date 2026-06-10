# -*- coding: utf-8 -*-
"""Integration tests for the IoC pipeline."""

from warc_zh_clean.pipelines import build_cleaner_pipeline, CleanerPipeline, PipelineStep
from warc_zh_clean.models import CleanContext, CleanResult
from warc_zh_clean.rules.pre_clean import PreCleanRule


def test_build_default_pipeline():
    """Pipeline builds from default YAML config."""
    pipeline = build_cleaner_pipeline()
    assert pipeline.name == "zh_clean_pipeline"
    assert len(pipeline.steps) == 7


def test_pipeline_accepts_good_record():
    """Pipeline accepts a well-formed long Chinese text."""
    pipeline = build_cleaner_pipeline()
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
    record = {"text": text, "category_label": "科技"}
    result = pipeline.process(record)
    assert result.clean_rec is not None
    assert result.dirty_rec is None


def test_pipeline_rejects_short_record():
    """Pipeline rejects text that is too short."""
    pipeline = build_cleaner_pipeline()
    record = {"text": "太短的文本", "category_label": "科技"}
    result = pipeline.process(record)
    assert result.clean_rec is None
    assert result.dirty_rec is not None


def test_pipeline_rejects_bad_category():
    """Pipeline rejects blocked category."""
    pipeline = build_cleaner_pipeline()
    long_text = "这是一段足够长的文本内容，" * 30
    record = {"text": long_text, "category_label": "赌博/色情/非法"}
    result = pipeline.process(record)
    assert result.clean_rec is None
    assert result.dirty_rec is not None


def test_pipeline_step_by_step():
    """Step-by-step execution reveals which step rejects."""
    pipeline = build_cleaner_pipeline()
    record = {"text": "太短的文本", "category_label": "科技"}
    steps_seen = []
    for step_name, ctx in pipeline.process_step_by_step(record):
        steps_seen.append(step_name)
        if ctx.rejected:
            assert ctx.reject_reason == "filter_rules_2"
            break
    assert "pre_clean" in steps_seen
    assert "chapter_filter" in steps_seen


def test_pipeline_apply_single_step():
    """Apply a single named step."""
    pipeline = build_cleaner_pipeline()
    record = {"text": "访问 https://example.com 获取信息", "category_label": "科技"}
    ctx = pipeline.apply_step("pre_clean", record)
    assert "<URL>" in ctx.text
    assert "example.com" not in ctx.text


def test_pipeline_apply_unknown_step():
    """Applying an unknown step raises KeyError."""
    pipeline = build_cleaner_pipeline()
    record = {"text": "test", "category_label": "科技"}
    try:
        pipeline.apply_step("nonexistent_step", record)
        assert False, "Expected KeyError"
    except KeyError:
        pass


def test_clean_context_reject():
    """CleanContext.reject() sets rejection fields."""
    ctx = CleanContext({"text": "hello"})
    ctx.reject("test_reason", "test_detail")
    assert ctx.rejected is True
    assert ctx.reject_reason == "test_reason"
    assert ctx.reject_detail == "test_detail"


def test_clean_context_build_clean_record():
    """build_clean_record strips trailing commas."""
    ctx = CleanContext({"text": "hello，", "category_label": "test"})
    ctx.text = "hello，"
    rec = ctx.build_clean_record()
    assert rec["text"] == "hello"


def test_clean_context_build_dirty_record():
    """build_dirty_record includes reject metadata."""
    ctx = CleanContext({"text": "hello", "category_label": "test"})
    ctx.reject("filter", "too_short")
    rec = ctx.build_dirty_record()
    assert "new_filter_detail" in rec
    assert "filter" in rec["new_filter_detail"]


def test_pipeline_result_clean():
    """CleanResult with clean_rec."""
    result = CleanResult(clean_rec={"text": "ok"}, dirty_rec=None)
    assert result.clean_rec is not None
    assert result.dirty_rec is None


def test_pipeline_result_dirty():
    """CleanResult with dirty_rec."""
    result = CleanResult(clean_rec=None, dirty_rec={"text": "bad", "new_filter_detail": "rejected"})
    assert result.clean_rec is None
    assert result.dirty_rec is not None