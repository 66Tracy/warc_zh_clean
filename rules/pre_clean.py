# -*- coding: utf-8 -*-
"""PreCleanRule: sensitive content replacement + symbol normalization.

This is a *transform* rule — it never rejects, only mutates ``ctx.text``.
"""

from warc_zh_clean import config as C
from warc_zh_clean.models import CleanContext
from warc_zh_clean.rules.base import BaseRule


# ---------------------------------------------------------------------------
# Pure helper functions (no ctx dependency)
# ---------------------------------------------------------------------------


def _extract_base(pattern, text, with_offset=False):
    """Base regex extractor."""
    if with_offset:
        return [
            {"text": item.group(1), "offset": (item.span()[0] - 1, item.span()[1] - 1)}
            for item in pattern.finditer(text)
        ]
    return [item.group(1) for item in pattern.finditer(text)]


def _extract_url(text, detail=False):
    """Extract URLs from text (with boundary padding)."""
    padded = "".join([C.URL_PAD_CHAR, text, C.URL_PAD_CHAR])
    return _extract_base(C.URL_RE, padded, with_offset=detail)


def _extract_email(text, detail=False):
    """Extract email addresses from text (with boundary padding)."""
    padded = "".join([C.EMAIL_PAD_CHAR, text, C.EMAIL_PAD_CHAR])
    results = _extract_base(C.EMAIL_RE, padded, with_offset=detail)
    if not detail:
        return results

    detail_results = []
    for item in results:
        domain_match = C.EMAIL_DOMAIN_RE.search(item["text"])
        if domain_match:
            item["domain_name"] = domain_match.group(1)
        detail_results.append(item)
    return detail_results


def _replace_sensitive(s: str) -> str:
    """Replace URLs and emails with placeholders."""
    url_list = _extract_url(s)
    for url in url_list:
        s = s.replace(url, "<URL>")

    email_list = _extract_email(s)
    for email in email_list:
        s = s.replace(email, "<EMAIL>")
    return s


def _document_replace(s: str) -> str:
    """Clean special characters from document text."""
    s = s.replace("\u00bb", "")   # »
    s = s.replace("\u00b6", "")   # ¶
    s = s.replace("\ufffd", "")   # �
    s = s.replace("/!", "!")
    s = s.replace("\u25a0", "")   # ■
    s = s.replace("!.", ".")
    s = s.replace("\u201e", ",")  # „
    return s


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


class PreCleanRule(BaseRule):
    """Replace sensitive content (URLs, emails) and normalize symbols.

    This rule never rejects a record.
    """

    def apply(self, ctx: CleanContext) -> CleanContext:
        ctx.text = _document_replace(_replace_sensitive(ctx.text))
        return ctx