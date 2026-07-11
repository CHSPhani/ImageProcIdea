import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fmt(x: float, nd: int = 3) -> str:
    return f"{x:.{nd}f}"


def pass_fail(satisfied: bool, score: float, tau: float) -> str:
    # We show both: logical satisfaction and score vs tau (because your current system separates them)
    logic = "PASS" if satisfied else "FAIL"
    strength = "OK" if score >= tau else "WEAK"
    return f"{logic} ({strength}, score={fmt(score)}, tau={fmt(tau)})"


def explain_compare(op: str) -> str:
    if op in ("<", "<="):
        return "Lower mean_intensity = darker = more covered (so LHS should be LOWER than RHS)."
    if op in (">", ">="):
        return "Higher mean_intensity = lighter (so LHS should be HIGHER than RHS)."
    return ""


def pretty_constraint(c: Dict[str, Any], tau: float) -> str:
    ctype = c.get("type", "")
    cid = c.get("id", "unknown")

    if ctype == "compare_means":
        lhs = c["lhs_set"]
        rhs = c["rhs_set"]
        op = c["op"]
        lhs_mean = c["lhs_mean"]
        rhs_mean = c["rhs_mean"]
        satisfied = c["satisfied"]
        score = c["score"]
        margin = c["margin"]

        head = f"- {cid}: mean({lhs}) {op} mean({rhs})"
        status = pass_fail(satisfied, score, tau)
        detail = (
            f"  • mean({lhs})={fmt(lhs_mean)}  mean({rhs})={fmt(rhs_mean)}  "
            f"margin={fmt(margin)}  ({explain_compare(op)})"
        )
        return f"{head}\n  • {status}\n{detail}"

    if ctype == "mean_threshold":
        s = c["set"]
        op = c["op"]
        thr = c["threshold"]
        mean_val = c["mean"]
        satisfied = c["satisfied"]
        score = c["score"]
        margin = c["margin"]

        head = f"- {cid}: mean({s}) {op} {thr}"
        status = pass_fail(satisfied, score, tau)
        detail = f"  • mean({s})={fmt(mean_val)}  threshold={fmt(thr)}  margin={fmt(margin)}"
        return f"{head}\n  • {status}\n{detail}"

    # fallback
    return f"- {cid}: Unsupported constraint type '{ctype}'"


def pretty_intent(item: Dict[str, Any], tau: float) -> str:
    iid = item["intent_id"]
    question = item["question"]
    raw = item["raw_intent"]
    alignment = item["alignment"]
    violations = item.get("violations", [])
    results = item.get("constraint_results", [])

    # Overall status: "PASS" if all constraints satisfied, else fail
    all_sat = all(r.get("satisfied", False) for r in results if "satisfied" in r)
    overall = "PASS" if all_sat else "FAIL"

    lines = []
    lines.append(f"Intent {iid}: {overall} (alignment={fmt(alignment)})")
    lines.append(f"Q: {question}")
    lines.append(f"User intent: {raw}")
    if violations:
        lines.append(f"Flags (score < {fmt(tau)}): {', '.join(violations)}")
    else:
        lines.append(f"Flags: none")
    lines.append("Constraints:")
    for c in results:
        lines.append(pretty_constraint(c, tau))
    return "\n".join(lines)


def generate_user_friendly_report(
    report_path: str,
    output_txt_path: str = None,
) -> str:
    report = load_json(report_path)
    tau = report.get("settings", {}).get("tau", 0.6)

    header = []
    header.append("SVCS Verification Summary (User-friendly)")
    header.append("-" * 60)
    header.append(f"Visual model: {report.get('visual_model')}")
    header.append(f"Derived predicates: {report.get('derived_predicates')}")
    header.append(f"Compiled intents: {report.get('compiled_intents')}")
    header.append(f"Settings: weighted_by_area={report.get('settings', {}).get('weighted_by_area')}  tau={fmt(tau)}")
    header.append("")
    header.append("Legend:")
    header.append("  PASS/FAIL = logical satisfaction of constraints")
    header.append("  OK/WEAK   = whether score >= tau (a confidence/strength flag)")
    header.append("  mean_intensity: lower means darker (more covered) in your current setup")
    header.append("-" * 60)
    header.append("")

    body = []
    for item in report.get("items", []):
        body.append(pretty_intent(item, tau))
        body.append("\n" + "-" * 60 + "\n")

    text = "\n".join(header + body)

    if output_txt_path is None:
        output_txt_path = str(Path(report_path).with_suffix(".summary.txt"))

    Path(output_txt_path).write_text(text, encoding="utf-8")
    return output_txt_path


if __name__ == "__main__":
    # Change this to your report path if needed
    report_path = str(Path(__file__).resolve().parent.parent / "Final_Result" / "barchart.verification_report.json")
    out_txt = generate_user_friendly_report(report_path)
    print(f"Wrote user-friendly summary: {out_txt}")