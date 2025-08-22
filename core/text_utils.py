# -*- coding: utf-8 -*-
"""Utility functions for text handling."""
import re


def detect_mojibake(text: str) -> bool:
    """Heuristic check for garbled Japanese text.

    This function is lightweight and has no external dependencies so that unit
    tests can run without the full Streamlit application environment.
    """
    if not text:
        return False
    suspicious_sequences = ["Ã", "Â", "�"]
    if any(seq in text for seq in suspicious_sequences):
        return True
    valid = re.compile(r"[\u0020-\u007E\u3000-\u30FF\u4E00-\u9FFF]+")
    valid_count = sum(1 for ch in text if valid.match(ch))
    return valid_count / len(text) < 0.7
