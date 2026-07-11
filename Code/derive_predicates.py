import json
from pathlib import Path

def derive_predicates(
    visual_model_path: str,
    output_path: str,
    band: float = 0.25,        # top/bottom/left/right bands
    center_lo: float = 0.35,   # center box lower bound
    center_hi: float = 0.65    # center box upper bound
) -> dict:
    vm = json.loads(Path(visual_model_path).read_text())

    W = vm["image_width"]
    H = vm["image_height"]
    objects = vm["objects"]

    preds = {
        "TOP": [],
        "BOTTOM": [],
        "LEFT": [],
        "RIGHT": [],
        "CENTER": [],
        "OUTER": [],
        "UPPER_RIGHT": [],
        "BOTTOM_OUTER": []
    }

    for obj in objects:
        oid = obj["id"]
        x, y = obj["centroid"]
        xn = x / float(W)
        yn = y / float(H)

        is_left = xn <= band
        is_right = xn >= (1.0 - band)
        is_top = yn <= band
        is_bottom = yn >= (1.0 - band)

        is_center = (center_lo <= xn <= center_hi) and (center_lo <= yn <= center_hi)
        is_outer = not is_center

        if is_top: preds["TOP"].append(oid)
        if is_bottom: preds["BOTTOM"].append(oid)
        if is_left: preds["LEFT"].append(oid)
        if is_right: preds["RIGHT"].append(oid)
        if is_center: preds["CENTER"].append(oid)
        if is_outer: preds["OUTER"].append(oid)

    # Derived combinations
    top_set = set(preds["TOP"])
    right_set = set(preds["RIGHT"])
    bottom_set = set(preds["BOTTOM"])
    outer_set = set(preds["OUTER"])

    preds["UPPER_RIGHT"] = sorted(list(top_set & right_set))
    preds["BOTTOM_OUTER"] = sorted(list(bottom_set & outer_set))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(preds, indent=2))
    return preds


if __name__ == "__main__":
    # Change this to your file path if needed
    ROOT = Path(__file__).resolve().parent.parent
    derive_predicates(str(ROOT / "JSONs" / "Original_Dest.json"),
                      str(ROOT / "derived_predicates" / "Original_Dest.derived_predicates.json"))
    print("Wrote derived_predicates.json")