---
created: 2026-06-17
updated: 2026-07-01
tags:
  - testing
  - ai
status: active
type: note
domain: work
parent: "[[50-maps/MOC-Evals-Observability]]"
seed: demo
---

# LLM-as-Judge Caveats

A model judge is a measurement instrument with known systematic errors and no calibration certificate. Used carefully, it scales grading you could never afford by hand; trusted naively, it laces every score with biases that point in consistent — and therefore corrupting — directions.

## The bias inventory

- **Verbosity preference.** Judges rate longer answers higher at equal correctness. Any change that makes an agent chattier will "improve" judged scores while users experience padding.
- **Position bias.** In pairwise comparisons, the first (or sometimes last) position wins more than it should. Never run a pairwise eval without swapping positions and averaging — the swap is not optional rigor, it is the measurement.
- **Self-preference.** Judges favor outputs from their own model family — enough to flip close comparisons. Cross-family judging or a judge panel dampens it.
- **Rubric drift.** Given a loose rubric, the judge invents its own standards, differently on different days. Tight, binary, per-criterion questions ("does the code handle the empty input: yes/no") are dramatically more stable than "rate quality 1-10."

## Calibrate or don't trust deltas

The only defensible use of a judge is *after* anchoring it to human labels: grade a sample by hand, measure judge-human agreement per criterion, and re-check on a cadence — agreement measured once is agreement assumed forever, which is how drift gets in ([[eval-drift-detection]] covers the cadence problem; the judge is one of the two things drifting).

If judge-human agreement on a criterion is below your tolerance, that criterion goes back to humans or gets restructured until it is mechanically checkable. Many "judgment" criteria are lazy encodings of checkable facts — "is the answer well-sourced" becomes "does it cite a file that exists."

## Design rules that survive contact

1. Binary criteria, one question each; aggregate outside the judge.
2. Pairwise with position swap for preferences; absolute rubrics for regressions ([[regression-pinning-evals]] needs absolute).
3. Log judge transcripts — an unexplained score you can't audit is not a score.
4. Prefer mechanical checks wherever one exists; spend the judge only where structure genuinely can't reach ([[eval-suite-design-for-agents]] orders the toolbox).
