# Benchmark Audit Agent — Capstone demo

## What it is
A runnable agent-workflow demo for the capstone task: audit a claim that Model A improves benchmark accuracy by 3 percentage points over Model B.

The browser app is self-contained and works offline. It exposes the plan, tool calls, trajectory, findings, and generated memo. The orchestration is **deterministic and rule-based**, not connected to an external LLM. This keeps all results reproducible and avoids implying that an external model or API was used.

The included CSV is **synthetic demonstration data** (2,504 rows, including four incomplete rows). It is not evidence of a real experiment or prior personal work. Replace it with your own results if the capstone requires data you actually collected.

## Run it
1. Unzip the project.
2. Open `index.html` in Chrome or Edge. No server, installation, API key, or internet connection is required.
3. Click **Run baseline** and inspect the first incorrect decision.
4. Click **Review improved plan**, then **Approve plan & run improved agent**.
5. Open **Trajectory**, **Findings**, and **Generated memo**.
6. Download the CSV or run the Python script for an independent reproduction.

## Reproduce with Python
Requires Python 3.9+ and no third-party packages:
```bash
python analyze.py benchmark_results.csv --mode paired
python analyze.py benchmark_results.csv --mode paired --json
python analyze.py benchmark_results.csv --mode baseline
```
The paired estimate uses a large-sample normal-approximation 95% interval for the mean of per-example differences. Category results are descriptive.

## Demo findings
- 2,504 raw rows; 2,500 complete matched pairs; four incomplete rows.
- Model A's paired accuracy is 3.00 percentage points higher overall.
- The paired 95% interval includes zero (approximately −0.04 to +6.04 pp), so the data do not establish a reliable improvement at the 5% level.
- Model B performs better in the Knowledge category.
- The flawed baseline treats matched rows as independent, omits missing-row reporting, and skips the category breakdown.

## Interview integrity
Run the app yourself before the interview and describe the run you actually inspected. Do not claim the synthetic data are your own benchmark, do not claim an LLM/API was connected, and do not state that you performed work you did not perform. A precise description is: a deterministic tool-using prototype with an orchestrator, validation/statistical tools, a trajectory, and a memo writer. You can discuss replacing the planner with an LLM while keeping validation and statistical computation deterministic.