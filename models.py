# -*- coding: utf-8 -*-
"""CleanContext and CleanResult for the IoC pipeline."""

from __future__ import annotations

from warc_zh_clean.config import DETAIL_FIELD


class CleanContext:
    """Mutable context object passed through each pipeline rule.

    Attributes:
        record: Original input record dict.
        text: Current text state (mutated by transform rules).
        category: category_label from the record.
        quality_label: quality_label from the record (if present).
        text_len: Length of text before line-level cleaning (set by set_text_len hook).
        text_removed: Number of characters removed by line cleaning.
        text_length_ratio: len(text) / text_len after line cleaning.
        rejected: Whether this record has been rejected by a filter rule.
        reject_reason: Short reason string if rejected.
        reject_detail: Detailed reject info if rejected.
        text_removed_none: Whether text became empty after cleaning.
    """

    __slots__ = (
        "record",
        "text",
        "category",
        "quality_label",
        "text_len",
        "text_removed",
        "text_length_ratio",
        "rejected",
        "reject_reason",
        "reject_detail",
        "text_removed_none",
    )

    def __init__(self, record: dict) -> None:
        self.record = record
        self.text = record.get("text", "")
        self.category = record.get("category_label", "")
        self.quality_label = record.get("quality_label", "")
        self.text_len = 0
        self.text_removed = 0
        self.text_length_ratio = 1.0
        self.rejected = False
        self.reject_reason = ""
        self.reject_detail = ""
        self.text_removed_none = False

    def reject(self, reason: str, detail: str = "") -> None:
        """Mark this context as rejected.

        Args:
            reason: Short reason identifier (e.g. "chapter_filter").
            detail: Optional detailed description.
        """
        self.rejected = True
        self.reject_reason = reason
        self.reject_detail = detail

    def build_clean_record(self) -> dict:
        """Build the output record for a clean (accepted) document.

        Returns:
            Record dict with updated text and optional detail field.
        """
        rec = dict(self.record)
        # Strip trailing commas
        text = self.text.strip().rstrip(",，").strip()
        rec["text"] = text
        if self.reject_detail:
            rec[DETAIL_FIELD] = self.reject_detail
        return rec

    def build_dirty_record(self) -> dict:
        """Build the output record for a dirty (rejected) document.

        Returns:
            Record dict with reject metadata.
        """
        rec = dict(self.record)
        rec[DETAIL_FIELD] = f"{self.reject_reason}: {self.reject_detail}" if self.reject_detail else self.reject_reason
        return rec


class CleanResult:
    """Result of processing a record through the pipeline.

    Attributes:
        clean_rec: Cleaned record dict if accepted, else None.
        dirty_rec: Original record with reject metadata if rejected, else None.
    """

    __slots__ = ("clean_rec", "dirty_rec")

    def __init__(self, clean_rec: dict | None, dirty_rec: dict | None) -> None:
        self.clean_rec = clean_rec
        self.dirty_rec = dirty_rec