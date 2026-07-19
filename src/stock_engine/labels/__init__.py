"""Label generation (training/eval only — never inference)."""

from stock_engine.labels.pipeline import LabelRunResult, run_label_publish

__all__ = ["LabelRunResult", "run_label_publish"]
