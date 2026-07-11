# ImageProcIdea — Semantic Visual Claim Verification

Given an image (a chart, a coverage map, ...) and a plain-English claim about what it should show,
can we automatically check whether the image actually backs up the claim?

That's the question this project explores. The pipeline segments an image into regions, computes
spatial/intensity statistics per region, and checks those statistics against a set of formal
constraints — producing a pass/fail verdict with a confidence score per claim, plus a human-readable
report explaining why.

```
image ──▶ segmentation (SLIC) ──▶ VisualModel JSON ──▶ derived predicates
                                                              │
intents.txt ──▶ compiled constraints ───────────────────────▶│
                                                              ▼
                                                   constraint evaluation
                                                              │
                                                              ▼
                                          verification report (JSON + plain-English summary)
```

This began as a different idea — image segmentation as a graph-coloring problem (see
[`Guide/PROJECT_IDEA.md`](Guide/PROJECT_IDEA.md) for the original pitch, still implemented in
`Code/segment_and_color.py`) — and evolved into the claim-verification system described here.

## What's actually implemented right now

Being upfront about the current state, since some of this is proof-of-concept:

- **Segmentation → VisualModel** (`Code/segment_and_color.py`, `Code/export_slic_to_visualmodel.py`):
  solid. SLIC superpixel segmentation (plus watershed / edge-based / brick-boundary / mortar-based
  variants), Region Adjacency Graph construction, greedy graph coloring, and export to a documented
  JSON schema (`svcs.visualmodel.v1`) with per-region centroid, bounding box, area, and mean
  color/intensity.
- **Predicate derivation** (`Code/derive_predicates.py`): solid. Buckets regions into spatial sets
  (TOP/BOTTOM/LEFT/RIGHT/CENTER/OUTER/UPPER_RIGHT/BOTTOM_OUTER) by normalized centroid position.
- **Constraint evaluation** (`Code/evaluate_svcs.py`): solid. Compares means across region sets,
  with configurable area-weighting and a pass/fail threshold (`tau`), and produces a scored,
  explainable report.
- **Intent "compiler"** (`Code/compile_intents.py`): **stubbed, not general yet.** It doesn't
  actually parse arbitrary English — `compile_constraints()` is a hardcoded lookup keyed by intent
  ID (`I1`..`I5`) that returns a hand-written constraint template for each. The five example
  intents in [`input_intents/intents.txt`](input_intents/intents.txt) (map coverage, bar/line/scatter
  trends) work because each ID has a matching template; a new `I6` would need its own template added
  by hand. This is the piece that would need real work (rule-based parsing, or an LLM) to generalize.
  A consequence you'll notice in the sample reports: the same fixed intent set gets evaluated
  against every test image regardless of chart type, so a couple of the sample verdicts (e.g. a bar
  chart evaluated against a "central region" map claim) are expected mismatches, not bugs.

## Repository layout

| Path | What it is |
|---|---|
| [`Code/`](Code) | The pipeline: segmentation, predicate derivation, intent compilation, evaluation, reporting |
| [`Guide/`](Guide) | Design docs — original project pitch, implementation notes, segmentation method reference |
| [`input_images/`](input_images) | Sample images (bar/line/scatter charts, brick/wood textures, a coverage map) |
| [`input_intents/intents.txt`](input_intents/intents.txt) | The example natural-language claims (`I1`–`I5`) |
| [`JSONs/`](JSONs) | Generated VisualModel JSON per image |
| [`derived_predicates/`](derived_predicates) | Generated spatial predicate sets per image |
| [`Final_Result/`](Final_Result) | Generated verification reports (JSON + plain-English `.summary.txt`) |
| [`results/`](results), [`SVCS_Images/`](SVCS_Images) | Generated visualizations (segmentation/coloring comparisons, sample coverage-map renders) |

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

## Running it

```bash
cd Code
python run_pipeline.py ../input_images/barchart.png
```

This runs all four pipeline stages and writes:
- `JSONs/barchart.json` — the VisualModel
- `derived_predicates/barchart.derived_predicates.json` — derived spatial predicates
- `input_intents/compiled_intents.json` — compiled constraints (from `intents.txt`)
- `Final_Result/barchart.verification_report.json` — the verdict, per intent and constraint

Omit the argument to run against the default sample (`input_images/barchart.png`).

For a plain-English version of a report:

```bash
python -c "from pretty_report import generate_user_friendly_report as g; g('../Final_Result/barchart.verification_report.json')"
```

which writes `Final_Result/barchart.verification_report.summary.txt` — see that file for a sample of what the output looks like (pass/fail per claim, the actual measured values, and why).

Verified working end-to-end with `opencv-python==5.0.0.93`, `scikit-image==0.26.0`,
`networkx==3.6.1`, `numpy==2.5.1`, `matplotlib==3.11.0` (pinned in `requirements.txt`).

## Docs

- [`Guide/PROJECT_IDEA.md`](Guide/PROJECT_IDEA.md) — the original graph-coloring pitch this evolved from
- [`Guide/IMPLEMENTATION_STEPS.md`](Guide/IMPLEMENTATION_STEPS.md) — segmentation → RAG → coloring, step by step
- [`Guide/Segmentation.md`](Guide/Segmentation.md), [`Guide/Standard_Segmentation_Methods.md`](Guide/Standard_Segmentation_Methods.md) — segmentation method reference

## License

No license is currently granted — all rights reserved. Shared here for review/portfolio purposes.
