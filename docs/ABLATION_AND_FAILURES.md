# Image-Level Ablation and Failure Analysis

This document records image-to-object experiments that were evaluated but are **not** promoted to the submission headline because their cross-sequence performance was insufficient.

## Why this matters

The strongest published CTC number in the submission is intentionally an association-isolation result using reference centroids as detections. The experiments below test whether that boundary can be removed using the actual DIC microscopy. They did not yet meet that standard.

Keeping the failures visible is part of the submission's reliability policy: weak image-level methods are not relabeled as end-to-end evidence.

## Experiment A — Generic percentile thresholding

Protocol:
- Raw DIC-C2DH-HeLa images.
- Candidate global intensity/residual thresholds.
- Connected components.
- Cross-sequence holdout.
- 6-pixel centroid match radius.
- 8 µm mutual-nearest-neighbor tracking.

Observed aggregate holdout:
- Detection precision: 0.00858
- Detection recall: 0.15178
- Detection F1: 0.01611
- Tracking edge F1: 0.04591

Conclusion: a generic thresholding baseline is not adequate for DIC-C2DH-HeLa.

## Experiment B — Classical DIC ridge segmentation

Protocol:
- Public KTH-SE-style multi-scale Hessian ridge response.
- Scales 5–10 px.
- Ridge normalization, thresholding and local-variance filtering.
- Cross-sequence holdout against CTC GT/SEG masks.

Observed aggregate:
- Mean GT-best IoU: 0.08726
- Mean matched IoU: 0.13852
- GT recall at IoU ≥ 0.5: 0.03924
- Predicted precision at IoU ≥ 0.5: 0.04769

Conclusion: the classical ridge baseline is reproducible but insufficient as the competition system's image detector.

## Experiment C — Lightweight supervised pixel/region model

Protocol:
- Random forest classifier.
- Training on CTC GT/SEG annotations from one sequence only.
- Evaluation on the other sequence.
- Multi-scale intensity, contrast, gradient, Hessian-eigenvalue and local-variance features.
- No external model weights.

Observed strict cross-sequence aggregate:
- Mean GT-best IoU: 0.20577
- Mean matched IoU: 0.19890
- GT recall at IoU ≥ 0.5: 0.04573
- Predicted precision at IoU ≥ 0.5: 0.09182

Conclusion: a lightweight supervised classical model improves over the ridge baseline in mean best-overlap, but remains far below a level suitable for an end-to-end claim.

## Submission decision

The current evidence therefore supports four distinct validation boundaries:

1. **Association evidence:** high-confidence temporal association using reference centroids.
2. **External graph evidence:** TRA/LNK with preserved CTC object geometry and no-oracle sensitivity control.
3. **Trajectory/phenotype evidence:** downstream preservation and controlled perturbation robustness.
4. **Image-level negative controls:** raw-image segmentation attempts are retained as documented failure analyses.

No image-level method is promoted into the headline benchmark until it passes strict cross-sequence validation at a scientifically useful accuracy level.

## Protocol correction — separate annotation roles

The CTC real-data annotations are not interchangeable. Gold tracking labels under `GT/TRA` provide the object identities and temporal links, but have weak object-region geometry. Gold segmentation labels under `GT/SEG` contain manually curated object shapes with sparse instance coverage. Silver segmentation under `ST/SEG` provides substantially denser masks but is not an independent manual gold standard. These distinctions follow the official CTC annotation guidance.

The current cross-sequence image-to-mask benchmark therefore trains and computes its dense, full-frame segmentation proxy against `ST/SEG`, while checking centroid detection and temporal links against the identities in `GT/TRA`. The temporal holdout benchmark also reports the IoU recall of individually annotated `GT/SEG` objects, but does not count detections on unlabeled cells as false positives in that sparse-gold check. Full-frame metrics against silver labels are explicitly identified as proxy metrics; they must not be described as independent human annotation scores.

The earlier experiment rows above are historical ablations, not proof that the current raw-image pipeline passes scientific validation. No image-to-phenotype method is promoted as validated until the current holdout quality gates pass and the limits of each annotation source are reported.
