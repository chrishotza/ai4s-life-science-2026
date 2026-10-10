"""Independent reviewer regression: identity QA must not eagerly import sklearn."""
from __future__ import annotations

import subprocess
import sys


def test_identity_and_threshold_import_without_sklearn_loaded():
    """Run a clean subprocess to exclude transitive imports from other tests."""
    program = """
import sys
# Simulate scikit-learn being unavailable, not merely not yet imported.
sys.modules['sklearn'] = None
import ai4s_imaging
from ai4s_imaging.identity_confidence import audit_track_color_continuity
from ai4s_imaging import segment_frames, instances_to_detections
from ai4s_imaging.supervised import Supervised2DSegmenter
assert callable(audit_track_color_continuity)
assert callable(segment_frames)
assert callable(instances_to_detections)
assert Supervised2DSegmenter().model is None
assert sys.modules['sklearn'] is None
"""
    result = subprocess.run([sys.executable, "-c", program],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
