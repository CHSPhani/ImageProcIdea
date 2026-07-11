import re
import json
from pathlib import Path

# ---- Project folders (repo root, resolved relative to this file) ----
ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = ROOT / "Code"
JSONS_DIR = ROOT / "JSONs"
PREDICATE_DIR = ROOT / "derived_predicates"
INTENTS_DIR = ROOT / "input_intents"
RESULT_DIR = ROOT / "Final_Result"

# Ensure folders exist
JSONS_DIR.mkdir(parents=True, exist_ok=True)
PREDICATE_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)


def safe_stem(path: Path) -> str:
    # "my.file.png" -> "my.file"
    return path.stem


def run_poc(image_path: str):
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    name = safe_stem(image_path)
    visual_model_path = JSONS_DIR / f"{name}.json"
    derived_pred_path = PREDICATE_DIR / f"{name}.derived_predicates.json"
    compiled_intents_path = INTENTS_DIR / "compiled_intents.json"
    report_path = RESULT_DIR / f"{name}.verification_report.json"

    # --- 1) Segment image -> VisualModel JSON ---
    # Expected: segment_and_color.py exposes a class or function to process one image.
    # If your API is different, tell me and I’ll adapt.
    from segment_and_color import comprehensive_visualization  # adjust if class name differs

    comprehensive_visualization(str(image_path))
    #proc.process_pipeline()

    # Your current code writes visual_model.json by default.
    # We rename/move it to JSONS/<imagename>.json
    # produced = Path("visual_model.json")
    # if not produced.exists():
    #     # If your segment script already writes directly, adjust here.
    #     raise FileNotFoundError(
    #         "segment_and_color did not produce visual_model.json in CWD. "
    #         "Either run from Code/ or update segment_and_color to write to JSONS_DIR."
    #     )

    # visual_model_path.write_text(produced.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[1/4] VisualModel JSON: {visual_model_path}")

    # --- 2) Derive predicates ---
    from derive_predicates import derive_predicates  # must exist

    derive_predicates(str(visual_model_path), str(derived_pred_path))
    print(f"[2/4] Derived predicates: {derived_pred_path}")

    # --- 3) Compile intents (once) ---
    # compile_intents.py must expose compile_intents(intents_path, output_path)
    from compile_intents import compile_intents

    intents_txt = INTENTS_DIR / "intents.txt"
    compile_intents(str(intents_txt), str(compiled_intents_path))
    print(f"[3/4] Compiled intents: {compiled_intents_path}")

    # --- 4) Evaluate ---
    from evaluate_svcs import evaluate  # must exist

    evaluate(
        visual_model_path=str(visual_model_path),
        derived_predicates_path=str(derived_pred_path),
        compiled_intents_path=str(compiled_intents_path),
        output_path=str(report_path),
        weighted_by_area=True,
        tau=0.6,
    )
    print(f"[4/4] Verification report: {report_path}")

    return str(report_path)


if __name__ == "__main__":
    import sys

    # Usage: python run_pipeline.py [path/to/image]
    # Defaults to input_images/barchart.png if no argument is given.
    INPUT_IMAGE = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "input_images" / "barchart.png")
    run_poc(INPUT_IMAGE)