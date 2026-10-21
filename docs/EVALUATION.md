# Evaluation protocol (planned)

No accuracy, precision, recall, or wildfire probability is reported for v0.1. Synthetic demo rows verify software behavior only. K-means silhouette measures cluster separation, not detection correctness.

1. Obtain labeled wildfire and non-wildfire observations with documented data rights, timestamp, geographic resolution, and label confidence.
2. Define the unit of evaluation (observation vs incident) and operational review objective before selecting metrics.
3. Split by region and time before tuning. Keep nearby detections and repeated views of the same event in one split to reduce leakage.
4. Compare the transparent priority baseline against confidence-only and FRP-only baselines. If supervised learning is justified, add a simple classifier before complex models.
5. Report precision-recall curves, false positives per region/day, recall at a fixed review budget, latency, missing-weather slices, and confidence intervals. Report calibration only for models producing evaluated probabilities.
6. Freeze a held-out test set and publish dataset version, seed, model/threshold version, failure examples and uncertainty. Do not tune to the test set.
7. Have a domain reviewer assess thermal industrial sources, agricultural burns, cloud/coverage gaps, and stale observations. Require prospective evaluation before operational claims.

Engineering verification is separate: parser rejection, transaction rollback, deduplication, distance/time grouping boundaries, workflow guards, report separation, GeoJSON coordinates, and HTTP validation.
