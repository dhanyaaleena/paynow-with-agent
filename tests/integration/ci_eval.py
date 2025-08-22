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
            ["python", "tests/integration/run_eval.py"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr, e.returncode

def parse_accuracy(output):
    """Parse accuracy percentages from evaluation output"""
    decision_match = re.search(r'Decision Accuracy: (\d+\.?\d*)%', output)
    reasons_match = re.search(r'Reasons Accuracy: (\d+\.?\d*)%', output)
    overall_match = re.search(r'Overall Accuracy: (\d+\.?\d*)%', output)
    accuracies = {}
    if decision_match:
        accuracies['decision'] = float(decision_match.group(1))
    if reasons_match:
        accuracies['reasons'] = float(reasons_match.group(1))
    if overall_match:
        accuracies['overall'] = float(overall_match.group(1))
    return accuracies

def check_accuracy_thresholds(accuracies):
    """Check if accuracies meet minimum thresholds"""
    thresholds = {
        'decision': 95.0,
        'reasons': 85.0,
        'overall': 85.0
    }
    failures = []
    for metric, threshold in thresholds.items():
        if metric in accuracies:
            if accuracies[metric] < threshold:
                failures.append(f"{metric.capitalize()} accuracy {accuracies[metric]}% is below threshold {threshold}%")
        else:
            failures.append(f"Could not determine {metric} accuracy")
    return failures

def main():
    print("Running Agent Evaluation for CI...")

    stdout, stderr, return_code = run_evaluation()

    # Always show detailed output for CI visibility
    print("\n===== Detailed evaluation output (run_eval.py) =====\n")
    if stdout:
        print(stdout)
    if stderr:
        print("\n[stderr]\n" + stderr)

    if return_code != 0:
        print("Evaluation script failed!")
        sys.exit(1)

    accuracies = parse_accuracy(stdout)

    if not accuracies:
        print("Could not parse accuracy metrics from evaluation output")
        sys.exit(1)

    failures = check_accuracy_thresholds(accuracies)

    if failures:
        print("Accuracy thresholds not met:")
        for failure in failures:
            print(f"  - {failure}")
        print("\nCurrent accuracies:")
        for metric, value in accuracies.items():
            print(f"  - {metric.capitalize()}: {value}%")
        sys.exit(1)

    print("All accuracy thresholds met!")
    print("Current accuracies:")
    for metric, value in accuracies.items():
        print(f"  - {metric.capitalize()}: {value}%")
    print("\nCI Evaluation passed successfully!")

if __name__ == "__main__":
    main()
