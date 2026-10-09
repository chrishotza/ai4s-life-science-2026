# ALFI Cellpose scale/polarity negative-control audit — 2026-10-09

**Conclusion: raw 1024×1280 resolution or contrast inversion did NOT improve the ALFI expert-instance F1 over the existing 512×640 normal-polarity CellposeSAM-v2 backend. Do not apply these transformations as defaults.**

[Successful all-three-variant GitHub Actions run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37973819292); evaluation code: [benchmark_alfi_scale_polarity.py](../scripts/benchmark_alfi_scale_polarity.py).

We audited each variant's original-file SHA256 manifest against the previously successful [frozen pretrained model race](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37972467985). **8/8 original image and expert-mask source hashes match** for each variant. The four fixed evaluation frames are ALFI MI05, MI06, MI07, MI08 at T0001, each with expert masks with 0 background, 128 interphase and 255 mitosis annotation. This is **posthoc** parameter diagnostics on a previously used evaluation cohort, not a pristine independent holdout.

| Pretrained cpsam_v2 variant | Mean pixel Dice | Mean frame instance F1@IoU50 | Matched GT instances | GT instances | Predicted instances |
|---|---:|---:|---:|---:|---:|
| 512×640, original polarity (previous run) | 0.40941 | **0.22821** | **12** | 71 | 40 |
| 1024×1280, original polarity | **0.44700** | 0.15795 | 8 | 71 | 35 |
| 1024×1280, inverted polarity | 0.41586 | 0.13530 | 7 | 71 | 38 |
| 512×640, inverted polarity | 0.41448 | 0.16697 | 9 | 71 | 36 |

It is important that native-scale pixel Dice improved, but the **instance F1 and number of matched cells both became worse**. Since interpretable tracks require distinct cell instances, pixel Dice alone should not select preprocessing.

By sequence, native original polarity matched MI05=1/7, MI06=4/21, MI07=1/25 and MI08=2/18 expert instances. Inverted native had 1/7, 4/21, 1/25 and 1/18. Normal original polarity at half resolution was 2/7, 6/21, 2/25 and 2/18.

**Scientific claim boundary:** Four frames only, ALFI masks may exclude visible unannotated cells. These parameter variations do not establish adequate full image-to-track-to-phenotype performance. Better segmentation requires domain-sensitive training or different instance-specific methods, not unvalidated polarity tricks. CTC results on DIC-C2DH-HeLa and ALFI results on another microscopy/annotation domain must not be averaged.

Source: ALFI dataset (Antonelli et al.), CC BY, https://doi.org/10.6084/m9.figshare.23798451.v1 . Upstream Cellpose pretrained weights carry third-party training-data usage constraints; assess rights before commercial reuse.
