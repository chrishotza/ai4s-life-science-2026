# Competition-Oriented Experiment Protocol

Freeze the current validated system before experimenting. A change is not accepted just because one metric rises.

## Baseline

Mutual-nearest-neighbor, 8.0 um gate, DIC-C2DH-HeLa 01/02:

- precision 0.99135
- recall 0.99322
- F1 0.99228
- mean trajectory coverage 0.9451
- directional-persistence MAE 0.0439

## Decision gates

Reject a candidate for a material regression:

- F1 drop > 0.002
- recall drop > 0.003
- coverage drop > 0.020
- persistence MAE increase > 0.010

Accept only when there is no critical regression, the internal utility score improves by > 0.002, and at least two measured dimensions improve.

The utility score is an internal iteration aid, not the Kaggle judging score.

## Commands

Single candidate:

~~~text
python scripts/ab_experiment.py --method mutual_nn --distance 8
~~~

Sweep principal public configurations:

~~~text
python scripts/ab_experiment.py --sweep
~~~

The CTC benchmark uses reference centroids as detections, so it evaluates tracking association and downstream trajectory preservation rather than end-to-end segmentation.
