#!/usr/bin/env python3
"""Reproducible paired benchmark audit. Python standard library only."""
import argparse, csv, json, math, sys
from collections import defaultdict
from pathlib import Path

REQUIRED = {"example_id", "category", "score_a", "score_b"}
Z95 = 1.96

def p_two_sided(z):
    return math.erfc(abs(z) / math.sqrt(2))

def load_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
        rows, seen = [], set()
        for line_no, raw in enumerate(reader, start=2):
            item = {k: (raw.get(k) or "").strip() for k in REQUIRED}
            if not item["example_id"] or not item["category"]:
                raise ValueError(f"Line {line_no}: example_id and category are required")
            if item["example_id"] in seen:
                raise ValueError(f"Line {line_no}: duplicate example_id {item['example_id']!r}")
            seen.add(item["example_id"])
            scores = {}
            for col in ("score_a", "score_b"):
                value = item[col]
                if value == "":
                    scores[col] = None
                else:
                    try: value = float(value)
                    except ValueError: raise ValueError(f"Line {line_no}: {col} is not numeric")
                    if value not in (0.0, 1.0):
                        raise ValueError(f"Line {line_no}: {col} must be 0, 1, or blank")
                    scores[col] = value
            rows.append({"example_id": item["example_id"], "category": item["category"], **scores})
    return rows

def analyze(rows, mode="paired"):
    complete = [r for r in rows if r["score_a"] is not None and r["score_b"] is not None]
    missing = len(rows) - len(complete)
    if not complete:
        raise ValueError("No complete matched pairs remain")
    if mode == "baseline":
        a = [r["score_a"] for r in rows if r["score_a"] is not None]
        b = [r["score_b"] for r in rows if r["score_b"] is not None]
        ma, mb = sum(a)/len(a), sum(b)/len(b)
        delta = ma - mb
        se = math.sqrt(ma*(1-ma)/len(a) + mb*(1-mb)/len(b))
        z = delta/se
        return {"mode": mode, "raw_rows": len(rows), "n_a": len(a), "n_b": len(b),
                "accuracy_a": ma, "accuracy_b": mb, "difference": delta,
                "se": se, "z": z, "p": p_two_sided(z),
                "ci": [delta-Z95*se, delta+Z95*se],
                "missing_unreported": missing}
    diffs = [r["score_a"] - r["score_b"] for r in complete]
    n = len(diffs)
    delta = sum(diffs)/n
    variance = sum((x-delta)**2 for x in diffs)/(n-1)
    se = math.sqrt(variance/n)
    z = delta/se
    groups = defaultdict(list)
    for r in complete:
        groups[r["category"]].append(r)
    categories = []
    for name, group in sorted(groups.items()):
        d = [r["score_a"]-r["score_b"] for r in group]
        categories.append({"category": name, "n": len(group),
            "accuracy_a": sum(r["score_a"] for r in group)/len(group),
            "accuracy_b": sum(r["score_b"] for r in group)/len(group),
            "difference": sum(d)/len(d)})
    return {"mode": mode, "raw_rows": len(rows), "complete_pairs": n,
            "missing": missing, "accuracy_a": sum(r["score_a"] for r in complete)/n,
            "accuracy_b": sum(r["score_b"] for r in complete)/n,
            "difference": delta, "se": se, "z": z, "p": p_two_sided(z),
            "ci": [delta-Z95*se, delta+Z95*se],
            "a_wins": sum(x == 1 for x in diffs),
            "b_wins": sum(x == -1 for x in diffs),
            "ties": sum(x == 0 for x in diffs), "categories": categories}

def memo(r):
    pp = lambda x: f"{100*x:.2f}%"
    if r["mode"] == "baseline":
        return (f"# Benchmark audit — baseline run\n\nModel A: {pp(r['accuracy_a'])} (n={r['n_a']}); "
                f"Model B: {pp(r['accuracy_b'])} (n={r['n_b']}).\n\n"
                f"Difference A − B: **{100*r['difference']:.2f} pp**. Unpaired 95% CI: "
                f"[{100*r['ci'][0]:.2f}, {100*r['ci'][1]:.2f}] pp; p={r['p']:.4f}.\n\n"
                "**Audit note:** this run treats matched scores as independent and does not "
                "report incomplete rows or category-level outcomes. It is not a valid final "
                "analysis for this paired benchmark.\n")
    lines = ["# Benchmark audit — paired run", "",
        f"Raw rows: **{r['raw_rows']}**; complete matched pairs: **{r['complete_pairs']}**; "
        f"incomplete rows: **{r['missing']}**.", "",
        f"Model A: **{pp(r['accuracy_a'])}**; Model B: **{pp(r['accuracy_b'])}**.", "",
        f"Paired difference A − B: **{100*r['difference']:.2f} pp**; 95% CI: "
        f"**[{100*r['ci'][0]:.2f}, {100*r['ci'][1]:.2f}] pp**; p={r['p']:.4f}.", "",
        f"Paired outcomes: A wins {r['a_wins']}; B wins {r['b_wins']}; ties {r['ties']}.", "",
        "## Category breakdown", "", "| Category | n | Model A | Model B | A − B |",
        "|---|---:|---:|---:|---:|"]
    for c in r["categories"]:
        lines.append(f"| {c['category']} | {c['n']} | {pp(c['accuracy_a'])} | "
                     f"{pp(c['accuracy_b'])} | {100*c['difference']:.2f} pp |")
    lines += ["", "**Verdict:** the point estimate is positive, but the paired 95% confidence "
        "interval includes zero. These data do not establish a reliable improvement at the "
        "5% level.", "", "Method: large-sample normal-approximation interval for the mean "
        "of per-example paired score differences. Category results are descriptive."]
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", nargs="?", default="benchmark_results.csv")
    parser.add_argument("--mode", choices=("paired", "baseline"), default="paired")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = analyze(load_rows(args.csv_path), args.mode)
    except Exception as exc:
        print("STOP:", exc, file=sys.stderr)
        sys.exit(2)
    print(json.dumps(result, indent=2) if args.json else memo(result))

if __name__ == "__main__":
    main()