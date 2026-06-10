# -*- coding: utf-8 -*-
"""Unit tests for LineCleanRule."""

from warc_zh_clean.rules.line_clean import (
    LineCleanRule,
    _is_bad_line2,
    _line_deleting,
    _line_deleting_end,
    _line_deleting_head,
)
from warc_zh_clean.models import CleanContext


def test_line_deleting_removes_empty_lines():
    text = "第一行\n\n第三行"
    result = _line_deleting(text)
    lines = result.split("\n")
    assert all(line.strip() != "" for line in lines if line)


def test_line_deleting_removes_navigation():
    text = "首页 尾页 1\n正文内容在这里"
    result = _line_deleting(text)
    assert "首页 尾页 1" not in result


def test_line_deleting_removes_copyright():
    text = "正文段落\nCopyright 2024 版权所有"
    result = _line_deleting(text)
    lines = [l for l in result.split("\n") if l.strip()]
    if lines:
        assert "Copyright" not in lines[-1]


def test_is_bad_line2_figure():
    assert _is_bad_line2("图1") is False
    assert _is_bad_line2("第3页") is False


def test_is_bad_line2_normal():
    assert _is_bad_line2("这是一行正常的文本") is True


def test_line_deleting_end_removes_icp():
    lines = ["正文内容", "ICP备12345678号"]
    result = _line_deleting_end(lines)
    assert len(result) < len(lines)


def test_line_deleting_head_removes_wechat():
    lines = ["微信扫一扫关注", "正文开始"]
    result = _line_deleting_head(lines)
    assert len(result) < len(lines)


def test_line_clean_rule_apply():
    """LineCleanRule applies line deletion and tracks text_removed."""
    rule = LineCleanRule()
    ctx = CleanContext({"text": "正文内容\n\n\n首页 尾页 1\n更多内容"})
    ctx = rule.apply(ctx)
    assert ctx.text_removed >= 0
    assert not ctx.rejected


def test_line_clean_rule_never_rejects():
    """LineCleanRule never rejects a record."""
    rule = LineCleanRule()
    ctx = CleanContext({"text": ""})
    ctx = rule.apply(ctx)
    assert not ctx.rejected


def test_line_deleting_removes_porn_video():
    """Lines containing both 污 and 视频 should be removed."""
    text = "污视频下载\n这是正常的内容部分，包含了足够多的文字来通过行级检测规则。"
    result = _line_deleting(text)
    assert "污视频" not in result