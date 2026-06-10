# -*- coding: utf-8 -*-
"""Unit tests for PreCleanRule."""

from warc_zh_clean.rules.pre_clean import (
    PreCleanRule,
    _replace_sensitive,
    _document_replace,
    _extract_url,
    _extract_email,
)
from warc_zh_clean.models import CleanContext


def test_replace_sensitive_url():
    text = "请访问 https://www.example.com 获取信息"
    result = _replace_sensitive(text)
    assert "<URL>" in result
    assert "example.com" not in result


def test_replace_sensitive_email():
    text = "发邮件到 test@example.com 联系我们"
    result = _replace_sensitive(text)
    assert "<EMAIL>" in result
    assert "test@example.com" not in result


def test_replace_sensitive_no_match():
    text = "这是一段普通文本没有任何链接或邮箱"
    result = _replace_sensitive(text)
    assert result == text


def test_document_replace_special_chars():
    text = "这是»一段¶带特殊■字符的文本"
    result = _document_replace(text)
    assert "\u00bb" not in result
    assert "\u00b6" not in result
    assert "\u25a0" not in result
    assert "这是" in result


def test_document_replace_comma():
    text = "他说\u201e你好\u201f"
    result = _document_replace(text)
    assert "\u201e" not in result
    assert "," in result


def test_extract_url_basic():
    text = "请访问 https://www.example.com 获取更多信息"
    urls = _extract_url(text)
    assert len(urls) >= 1
    assert "example.com" in urls[0]


def test_extract_url_none():
    text = "这是一段没有链接的普通中文文本"
    urls = _extract_url(text)
    assert len(urls) == 0


def test_extract_email_basic():
    text = "请联系 test@example.com 获取信息"
    emails = _extract_email(text)
    assert len(emails) >= 1
    assert "test@example.com" in emails[0]


def test_extract_email_none():
    text = "这段文字没有任何邮箱地址"
    emails = _extract_email(text)
    assert len(emails) == 0


def test_extract_url_with_detail():
    text = "访问 https://www.example.com/path 页面"
    results = _extract_url(text, detail=True)
    assert len(results) >= 1
    assert "text" in results[0]
    assert "offset" in results[0]


def test_pre_clean_rule_apply():
    """PreCleanRule applies both replace and document_replace."""
    rule = PreCleanRule()
    ctx = CleanContext({"text": "访问 https://example.com 页面»，段落¶结束"})
    ctx = rule.apply(ctx)
    assert "<URL>" in ctx.text
    assert "\u00bb" not in ctx.text
    assert "\u00b6" not in ctx.text
    assert not ctx.rejected


def test_pre_clean_rule_never_rejects():
    """PreCleanRule never rejects a record."""
    rule = PreCleanRule()
    ctx = CleanContext({"text": ""})
    ctx = rule.apply(ctx)
    assert not ctx.rejected