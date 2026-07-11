import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Union

Number = Union[int, float]


def load_json(p: str) -> Dict[str, Any]:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def resolve_set(
    set_spec: Union[str, Dict[str, Any]],
    predicates: Dict[str, List[int]],
) -> Set[int]:
    """
    set_spec can be:
      - "CENTER" (string referencing predicates)
      - {"set_diff": ["OUTER", "UPPER_RIGHT"]} meaning OUTER \\ UPPER_RIGHT
    """
    if isinstance(set_spec, str):
        if set_spec not in predicates:
            raise KeyError(f"Unknown predicate set: {set_spec}")
        return set(predicates[set_spec])

    if isinstance(set_spec, dict):
        if "set_diff" in set_spec:
            a, b = set_spec["set_diff"]
            A = resolve_set(a, predicates)
            B = resolve_set(b, predicates)
            return A - B

    raise ValueError(f"Unsupported set spec: {set_spec}")


def mean_metric_over_set(
    objects_by_id: Dict[int, Dict[str, Any]],
    ids: Set[int],
    metric: str,
    weighted_by_area: bool = True,
) -> float:
    if not ids:
        raise ValueError("Empty set for mean computation")

    if weighted_by_area:
        num = 0.0
        den = 0.0
        for i in ids:
            obj = objects_by_id[i]
            w = float(obj.get("area", 1.0))
            num += float(obj[metric]) * w
            den += w
        return num / den if den > 0 else float("nan")

    vals = [float(objects_by_id[i][metric]) for i in ids]
    return sum(vals) / len(vals)


def compare(op: str, lhs: float, rhs: float) -> bool:
    if op == "<":
        return lhs < rhs
    if op == "<=":
        return lhs <= rhs
    if op == ">":
        return lhs > rhs
    if op == ">=":
        return lhs >= rhs
    if op == "==":
        return lhs == rhs
    raise ValueError(f"Unsupported operator: {op}")


def constraint_score(op: str, lhs: float, rhs: float) -> Tuple[float, float]:
    """
    Returns (score in [0,1], margin).
    margin is defined so that positive => "good" (supports satisfaction).
    score is a simple normalized function of margin (v0).
    """
    if op in ("<", "<="):
        margin = rhs - lhs
    elif op in (">", ">="):
        margin = lhs - rhs
    else:
        margin = -abs(lhs - rhs)

    scale = max(1e-6, abs(rhs), abs(lhs), 0.1)
    raw = 0.5 + (margin / (2.0 * scale))
    score = max(0.0, min(1.0, raw))
    return score, margin


def eval_constraint(
    c: Dict[str, Any],
    objects_by_id: Dict[int, Dict[str, Any]],
    predicates: Dict[str, List[int]],
    weighted_by_area: bool = True,
) -> Dict[str, Any]:
    ctype = c["type"]
    metric = c.get("metric", "mean_intensity")

    if ctype == "compare_means":
        lhs_ids = resolve_set(c["lhs_set"], predicates)
        rhs_ids = resolve_set(c["rhs_set"], predicates)

        lhs_mean = mean_metric_over_set(objects_by_id, lhs_ids, metric, weighted_by_area)
        rhs_mean = mean_metric_over_set(objects_by_id, rhs_ids, metric, weighted_by_area)

        op = c["op"]
        sat = compare(op, lhs_mean, rhs_mean)
        score, margin = constraint_score(op, lhs_mean, rhs_mean)

        return {
            "id": c["id"],
            "type": ctype,
            "metric": metric,
            "lhs_set": c["lhs_set"],
            "rhs_set": c["rhs_set"],
            "lhs_mean": lhs_mean,
            "rhs_mean": rhs_mean,
            "op": op,
            "satisfied": bool(sat),
            "score": float(score),
            "margin": float(margin),
            "lhs_count": len(lhs_ids),
            "rhs_count": len(rhs_ids),
        }

    if ctype == "mean_threshold":
        ids = resolve_set(c["set"], predicates)
        mean_val = mean_metric_over_set(objects_by_id, ids, metric, weighted_by_area)
        op = c["op"]
        thr = float(c["threshold"])
        sat = compare(op, mean_val, thr)
        score, margin = constraint_score(op, mean_val, thr)

        return {
            "id": c["id"],
            "type": ctype,
            "metric": metric,
            "set": c["set"],
            "mean": mean_val,
            "op": op,
            "threshold": thr,
            "satisfied": bool(sat),
            "score": float(score),
            "margin": float(margin),
            "count": len(ids),
        }

    return {
        "id": c.get("id", "unknown"),
        "type": ctype,
        "satisfied": False,
        "score": 0.0,
        "error": f"Unsupported constraint type: {ctype}"
    }


def evaluate(
    visual_model_path: str,
    derived_predicates_path: str,
    compiled_intents_path: str,
    output_path: str,
    weighted_by_area: bool = True,
    tau: float = 0.6,
) -> Dict[str, Any]:
    vm = load_json(visual_model_path)
    preds = load_json(derived_predicates_path)
    intents = load_json(compiled_intents_path)

    objects_by_id = {int(o["id"]): o for o in vm["objects"]}

    report = {
        "schema": "svcs.verification_report.v1",
        "visual_model": visual_model_path,
        "derived_predicates": derived_predicates_path,
        "compiled_intents": compiled_intents_path,
        "settings": {"weighted_by_area": weighted_by_area, "tau": tau},
        "items": []
    }

    for item in intents["items"]:
        results = []
        for c in item["constraints"]:
            try:
                results.append(eval_constraint(c, objects_by_id, preds, weighted_by_area))
            except Exception as e:
                results.append({
                    "id": c.get("id", "unknown"),
                    "type": c.get("type", "unknown"),
                    "satisfied": False,
                    "score": 0.0,
                    "error": str(e)
                })

        scores = [r.get("score", 0.0) for r in results]
        alignment = sum(scores) / max(1, len(scores))
        violations = [r["id"] for r in results if r.get("score", 0.0) < tau]

        report["items"].append({
            "intent_id": item["intent_id"],
            "question": item["question"],
            "raw_intent": item["raw_intent"],
            "alignment": float(alignment),
            "violations": violations,
            "constraint_results": results
        })

    Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def default_paths_for_visual_model(visual_model_path: str) -> Dict[str, str]:
    """
    Given <repo_root>/JSONs/Original_Dest.json, resolve the default sibling paths:
      derived predicates: <repo_root>/derived_predicates/derived_predicates.json
      compiled intents:   <repo_root>/input_intents/compiled_intents.json
      output report:      <repo_root>/Final_Result/verification_report.json
    """
    root = Path(visual_model_path).resolve().parent.parent

    intents_path = root / "input_intents" / "compiled_intents.json"
    derived_path = root / "derived_predicates" / "derived_predicates.json"
    out_path = root / "Final_Result" / "verification_report.json"

    return {
        "derived_predicates_path": str(derived_path),
        "compiled_intents_path": str(intents_path),
        "output_path": str(out_path),
    }


if __name__ == "__main__":
    # ---- USER INPUT (your example) ----
    visual_model_path = str(Path(__file__).resolve().parent.parent / "JSONs" / "Original_Dest.json")

    # ---- AUTO PATHS ----
    paths = default_paths_for_visual_model(visual_model_path)
    derived_predicates_path = paths["derived_predicates_path"]
    compiled_intents_path = paths["compiled_intents_path"]
    output_path = paths["output_path"]

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # ---- RUN ----
    evaluate(
        visual_model_path=visual_model_path,
        derived_predicates_path=derived_predicates_path,
        compiled_intents_path=compiled_intents_path,
        output_path=output_path,
        weighted_by_area=True,
        tau=0.6,
    )
    print(f"Wrote: {output_path}")