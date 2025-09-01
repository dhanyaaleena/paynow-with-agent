#!/usr/bin/env python3
"""
CI Evaluation Script
Runs the agent evaluation and checks for minimum accuracy thresholds.
Fails CI if accuracy drops below acceptable levels.
"""

import subprocess
import sys
import json
import re

def run_evaluation():
    """Run the evaluation script and capture output"""
    try:
        result = subprocess.run(
            ["python", "backend/tests/integration/run_eval.py"], 
            capture_output=True, 
            text=True, 
            check=True,
            cwd="."
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr, e.returncode

def parse_accuracy(output):
    """Parse accuracy percentages from evaluation output"""
    decision_match = re.search(r'Decision Accuracy:\s*(\d+\.\d+%)', output)
    reasons_match = re.search(r'Reasons Accuracy:\s*(\d+\.\d+%)', output)
    overall_match = re.search(r'Overall Accuracy:\s*(\d+\.\d+%)', output)

    def pct_to_float(m):
        if not m:
            return None
        return float(m.group(1).rstrip('%'))

    return {
        'decision': pct_to_float(decision_match),
        'reasons': pct_to_float(reasons_match),
        'overall': pct_to_float(overall_match),
    }

def check_accuracy_thresholds(accuracies):
    """Check if accuracies meet minimum thresholds"""
    thresholds = {
        'decision': 95.0,
        'reasons': 85.0,
        'overall': 85.0,
    }
    failures = []
    for metric, threshold in thresholds.items():
        v = accuracies.get(metric)
        if v is None:
            failures.append(f"Could not determine {metric} accuracy")
        elif v < threshold:
            failures.append(f"{metric.capitalize()} accuracy {v}% is below threshold {threshold}%")
    return failures

def main():
    print("Running Agent Evaluation for CI...")

    stdout, stderr, return_code = run_evaluation()

    # Always print full raw output for visibility (mimics run_eval.py detail)
    print("\n===== Raw evaluation output (from run_eval.py) =====\n")
    if stdout:
        print(stdout)
    if stderr:
        print("\n===== STDERR =====\n")
        print(stderr)

    if return_code != 0:
        print("Evaluation script failed!")
        sys.exit(1)

    accuracies = parse_accuracy(stdout or "")
    if not accuracies or any(v is None for v in accuracies.values()):
        print("Could not parse accuracy metrics from evaluation output")
        sys.exit(1)

    failures = check_accuracy_thresholds(accuracies)
    if failures:
        print("Accuracy thresholds not met:")
        for f in failures:
            print(f"  - {f}")
        print("\nCurrent accuracies:")
        for k, v in accuracies.items():
            print(f"  - {k.capitalize()}: {v}%")
        sys.exit(1)

    print("All accuracy thresholds met!")
    print("Current accuracies:")
    for k, v in accuracies.items():
        print(f"  - {k.capitalize()}: {v}%")
    print("\nCI Evaluation passed successfully!")

if __name__ == "__main__":
    main()
