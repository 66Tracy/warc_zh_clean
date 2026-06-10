# -*- coding: utf-8 -*-
"""BaseRule abstract base class."""

from abc import ABC, abstractmethod

from warc_zh_clean.models import CleanContext


class BaseRule(ABC):
    """Abstract base class for all pipeline rules.

    Subclasses must implement ``apply(ctx)`` which mutates the
    ``CleanContext`` in-place and returns it.
    """

    @abstractmethod
    def apply(self, ctx: CleanContext) -> CleanContext:
        """Apply this rule to the context.

        Args:
            ctx: Mutable cleaning context.

        Returns:
            The same context object (mutated in-place).
        """

    @property
    def name(self) -> str:
        """Human-readable rule name (defaults to class name)."""
        return self.__class__.__name__