"""Lightweight microscopy detection and segmentation methods."""

from .cellpose_backend import CellposeSegmenter
from .segment import segment_frames
from .boxes import instances_to_box_detections
from .supervised import Supervised2DSegmenter, instances_to_detections

__all__ = [
    "segment_frames",
    "Supervised2DSegmenter",
    "CellposeSegmenter",
    "instances_to_detections",
    "instances_to_box_detections",
]
