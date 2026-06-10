# -*- coding: utf-8 -*-
"""CleanerPipeline executor and PipelineStep."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from warc_zh_clean.models import CleanContext, CleanResult
from warc_zh_clean.rules.base import BaseRule


@dataclass
class PipelineStep:
    """A single step in the cleaning pipeline.

    Attributes:
        name: Step name (for logging/debugging).
        rule: BaseRule instance (if type is "rule").
        hook: Callable hook function (if type is "hook").
        is_hook: Whether this step is a hook (not a rule).
    """

    name: str
    rule: BaseRule | None = None
    hook: Callable[[CleanContext], CleanContext] | None = None
    is_hook: bool = False

    def execute(self, ctx: CleanContext) -> CleanContext:
        """Execute this step on the context.

        Args:
            ctx: Mutable cleaning context.

        Returns:
            The same context object (mutated in-place).
        """
        if self.is_hook and self.hook is not None:
            return self.hook(ctx)
        if self.rule is not None:
            return self.rule.apply(ctx)
        return ctx


class CleanerPipeline:
    """Executor that runs a sequence of PipelineSteps on a CleanContext.

    Supports:
    - ``process()``: run all steps, return CleanResult.
    - ``process_step_by_step()``: run step-by-step, yield intermediate states.
    - ``apply_step()``: run a single named step.
    """

    def __init__(self, name: str, steps: list[PipelineStep]) -> None:
        self.name = name
        self.steps = steps
        self._step_map = {s.name: s for s in steps}

    def process(self, record: dict) -> CleanResult:
        """Process a record through all pipeline steps.

        Args:
            record: Input record dict.

        Returns:
            CleanResult with clean_rec or dirty_rec populated.
        """
        ctx = CleanContext(record)

        for step in self.steps:
            if ctx.rejected:
                break
            step.execute(ctx)

        if ctx.rejected:
            return CleanResult(clean_rec=None, dirty_rec=ctx.build_dirty_record())
        return CleanResult(clean_rec=ctx.build_clean_record(), dirty_rec=None)

    def process_step_by_step(self, record: dict):
        """Process a record, yielding (step_name, ctx) after each step.

        Useful for debugging — you can see which step rejects a record.

        Args:
            record: Input record dict.

        Yields:
            (step_name, CleanContext) tuples after each step executes.
        """
        ctx = CleanContext(record)

        for step in self.steps:
            if ctx.rejected:
                break
            step.execute(ctx)
            yield step.name, ctx

    def apply_step(self, step_name: str, record: dict) -> CleanContext:
        """Apply a single named step to a record.

        Args:
            step_name: Name of the step to execute.
            record: Input record dict.

        Returns:
            CleanContext after the step executes.

        Raises:
            KeyError: If step_name is not found.
        """
        if step_name not in self._step_map:
            raise KeyError(f"Step '{step_name}' not found in pipeline '{self.name}'")
        ctx = CleanContext(record)
        self._step_map[step_name].execute(ctx)
        return ctx