#!python
"""Shared paths and helpers for taxonorm README examples."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SHORTS_DIR = PROJECT_ROOT / "Samples" / "Variants" / "Shorts"
CHUNKS_DIR = PROJECT_ROOT / "Samples" / "Variants" / "Chunks"
SAMPLE_IP_H_K_T = SHORTS_DIR / "U_IP_H_K_T.csv"
SAMPLE_LP_H_I_NS = SHORTS_DIR / "U_LP_H_I_NS.csv"
SAMPLE_IP_CHUNKS = CHUNKS_DIR / "IP_Chunks.csv"
LEAF_KEYS = ["en_US", "uk_UA"]


def as_int_when_possible(value: Any) -> Any:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value
