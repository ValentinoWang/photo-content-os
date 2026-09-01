#!/usr/bin/env python3
"""Small standard-library helpers shared by document contract checks."""

from __future__ import annotations


def missing_markers(text: str, markers: list[str]) -> list[str]:
    """Return every required marker that does not occur in ``text``."""
    return [marker for marker in markers if marker not in text]
