import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple


# --------- CONFIG (v0 assumptions) ----------
# If "more covered" means darker, and mean_intensity is grayscale in [0,1],
# then darker -> lower intensity. So "more covered" => lower mean_intensity.
MORE_COVERED_OP = "<"   # flip to ">" if encoding is opposite


# --------- Helpers ----------
# This function reads a text file containing intents, where each line follows the format "I#: some intent text...". It returns a list of tuples, where each tuple contains the intent ID (e.g., "I1") and the corresponding intent text. The function also includes error handling for missing files and incorrect line formats.
def parse_intents_file(path: str) -> List[Tuple[str, str]]:
    """
    Reads intents.txt where each line is like:
      I1: some intent text...
    Returns list of (intent_id, intent_text).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Intents file not found: {path}")

    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    intents = []
    for ln in lines:
        m = re.match(r"^(I\d+)\s*:\s*(.+)$", ln)
        if not m:
            raise ValueError(f"Bad line format (expected 'I#: ...'): {ln}")
        intents.append((m.group(1), m.group(2)))
    return intents

# This function generates a yes/no question based on the intent ID and text. It uses predefined templates for known intent IDs (I1 to I5) to create specific questions that can be evaluated against the visual model. If the intent ID is not recognized, it falls back to a generic question format that references the intent ID.
def make_question(intent_id: str, intent_text: str) -> str:
    """
    Converts intent to a crisp yes/no verification question.
    """
    # Simple v0 question templates based on ID. (Keeps it deterministic.)
    if intent_id == "I1":
        return "Are central regions more covered than outer regions (with outer still non-zero covered)?"
    if intent_id == "I2":
        return ("Are most outer regions less covered than the center, "
                "but upper-right and bottom-outer regions more covered than other outer regions?")
    if intent_id == "I3":
        return "Are the right-side regions (proxy for bars on the right) more covered than left-side regions?"
    if intent_id == "I4":
        return "Is there a left-to-right increase in activity (proxy: right side more covered than left side)?"
    if intent_id == "I5":
        return "Is the upper half denser/more covered than the lower half?"
    # fallback:
    return f"Does the visualization satisfy intent {intent_id}?"

# This function compiles a given intent into a list of formal constraints that can be evaluated against the visual model. Each constraint is represented as a dictionary with details about the type of constraint, the metric to evaluate, the sets involved, and the operator for comparison. The function handles specific intents (I1 to I5) with predefined constraints and provides a fallback for unknown intents.
def compile_constraints(intent_id: str, intent_text: str) -> List[Dict[str, Any]]:
    """
    Hardcoded mapping from intent to formal constraints over predicate sets.
    Constraints are templates; evaluation will compute means over the sets.
    """
    constraints: List[Dict[str, Any]] = []

    # Common fields
    metric = "mean_intensity"
    op_more = MORE_COVERED_OP  # "<" means lower intensity => more covered

    if intent_id == "I1":
        # c1: mean(CENTER) more covered than mean(OUTER)
        constraints.append({
            "id": "c1_center_vs_outer",
            "type": "compare_means",
            "metric": metric,
            "lhs_set": "CENTER",
            "op": op_more,
            "rhs_set": "OUTER"
        })
        # c1b: outer not zero (outer still covered a bit)
        constraints.append({
            "id": "c1b_outer_nonzero",
            "type": "mean_threshold",
            "metric": metric,
            # If more covered => lower intensity, "nonzero coverage" means: outer not *too* bright.
            # We express it as: mean(OUTER) <= max_brightness (tunable).
            "set": "OUTER",
            "op": "<=",
            "threshold": 0.95  # tune later
        })
        return constraints

    if intent_id == "I2":
        # c2: center more covered than outer
        constraints.append({
            "id": "c2_center_vs_outer",
            "type": "compare_means",
            "metric": metric,
            "lhs_set": "CENTER",
            "op": op_more,
            "rhs_set": "OUTER"
        })
        # c2a: upper-right more covered than other outer
        constraints.append({
            "id": "c2a_upper_right_outer_vs_other_outer",
            "type": "compare_means",
            "metric": metric,
            "lhs_set": "UPPER_RIGHT",
            "op": op_more,
            "rhs_set": {"set_diff": ["OUTER", "UPPER_RIGHT"]}
        })
        # c2b: bottom-outer more covered than other outer
        constraints.append({
            "id": "c2b_bottom_outer_vs_other_outer",
            "type": "compare_means",
            "metric": metric,
            "lhs_set": "BOTTOM_OUTER",
            "op": op_more,
            "rhs_set": {"set_diff": ["OUTER", "BOTTOM_OUTER"]}
        })
        return constraints

    if intent_id == "I3":
        # Proxy: right side more covered than left side
        constraints.append({
            "id": "c3_right_vs_left",
            "type": "compare_means",
            "metric": metric,
            "lhs_set": "RIGHT",
            "op": op_more,
            "rhs_set": "LEFT"
        })
        return constraints

    if intent_id == "I4":
        # V0 proxy for increasing trend: right side more covered than left side
        constraints.append({
            "id": "c4_right_vs_left_proxy_trend",
            "type": "compare_means",
            "metric": metric,
            "lhs_set": "RIGHT",
            "op": op_more,
            "rhs_set": "LEFT"
        })
        return constraints

    if intent_id == "I5":
        # upper half denser than lower half
        constraints.append({
            "id": "c5_top_vs_bottom",
            "type": "compare_means",
            "metric": metric,
            "lhs_set": "TOP",
            "op": op_more,
            "rhs_set": "BOTTOM"
        })
        return constraints

    # fallback: no constraints
    constraints.append({
        "id": f"c_unknown_{intent_id}",
        "type": "uncompiled",
        "raw_intent": intent_text
    })
    return constraints


# This is the main function that compiles intents into a structured JSON format for evaluation.
# It reads the intents from a text file, generates questions and formal constraints, and saves the compiled result to a JSON file.
# The output JSON includes metadata about the schema and assumptions, as well as a list of items where each item corresponds to an intent with its question and constraints.
def compile_intents(intents_path: str, output_path: str) -> Dict[str, Any]:
    intents = parse_intents_file(intents_path)
    compiled = {
        "schema": "svcs.intent_compiler.v1",
        "source_file": intents_path,
        "assumptions": {
            "metric": "mean_intensity",
            "more_covered_operator": MORE_COVERED_OP,
            "note": "If your intensity encoding is opposite, flip more_covered_operator."
        },
        "items": []
    }

    for intent_id, intent_text in intents:
        item = {
            "intent_id": intent_id,
            "raw_intent": intent_text,
            "question": make_question(intent_id, intent_text),
            "constraints": compile_constraints(intent_id, intent_text),
        }
        compiled["items"].append(item)

    Path(output_path).write_text(json.dumps(compiled, indent=2), encoding="utf-8")
    return compiled


if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent.parent
    intents_path = ROOT / "input_intents" / "intents.txt"
    output_path = ROOT / "input_intents" / "compiled_intents.json"

    compile_intents(str(intents_path), str(output_path))
    print(f"Wrote: {output_path}")