# -*- coding: utf-8 -*-
"""Pipeline builder: YAML config -> CleanerPipeline."""

from __future__ import annotations

from pathlib import Path

import yaml

from warc_zh_clean.pipelines.executor import CleanerPipeline, PipelineStep
from warc_zh_clean.pipelines.registry import RULE_REGISTRY, HOOK_REGISTRY


_DEFAULT_CONFIG = Path(__file__).parent / "configs" / "zh_pipeline.yaml"


def build_cleaner_pipeline(config_path: str | Path | None = None) -> CleanerPipeline:
    """Build a CleanerPipeline from a YAML configuration file.

    Args:
        config_path: Path to YAML file. Defaults to the built-in
            ``configs/zh_pipeline.yaml``.

    Returns:
        Configured CleanerPipeline instance.

    Raises:
        KeyError: If a rule class or hook handler name is not in the registry.
        FileNotFoundError: If config_path does not exist.
    """
    if config_path is None:
        config_path = _DEFAULT_CONFIG
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    pipeline_name = cfg.get("name", "unnamed_pipeline")
    steps = []

    for step_cfg in cfg["steps"]:
        step_name = step_cfg["name"]
        step_type = step_cfg.get("type", "rule")

        if step_type == "rule":
            class_name = step_cfg["class"]
            if class_name not in RULE_REGISTRY:
                raise KeyError(
                    f"Rule class '{class_name}' not found in RULE_REGISTRY. "
                    f"Available: {list(RULE_REGISTRY.keys())}"
                )
            rule_instance = RULE_REGISTRY[class_name]()
            steps.append(PipelineStep(name=step_name, rule=rule_instance, is_hook=False))

        elif step_type == "hook":
            handler_name = step_cfg["handler"]
            if handler_name not in HOOK_REGISTRY:
                raise KeyError(
                    f"Hook handler '{handler_name}' not found in HOOK_REGISTRY. "
                    f"Available: {list(HOOK_REGISTRY.keys())}"
                )
            hook_fn = HOOK_REGISTRY[handler_name]
            steps.append(PipelineStep(name=step_name, hook=hook_fn, is_hook=True))

        else:
            raise ValueError(f"Unknown step type '{step_type}' in step '{step_name}'")

    return CleanerPipeline(name=pipeline_name, steps=steps)