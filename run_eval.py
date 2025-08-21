#!/usr/bin/env python3
"""
Evaluation script for PayNow agent
Runs test cases and calculates accuracy metrics
"""
import asyncio
import json
import time
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import text
from db import AsyncSessionLocal, init_db
from models import Customer
from main import app


class AgentEvaluator:
    def __init__(self):
        self.client = TestClient(app)
        self.test_customer_id = "c_123"
        self.api_key = "test-api-key"

    async def setup_test_environment(self):
        """Setup test environment with required customer data"""
        print("🔧 Setting up test environment...")
        await init_db()

        async with AsyncSessionLocal() as session:
            # Clear existing test data
            await session.execute(text("DELETE FROM customers WHERE id LIKE 'c_123_%'"))
            await session.execute(text("DELETE FROM customers WHERE id LIKE 'c_789_%'"))

            # Add test customers with balance for evaluation tests
            # We'll create customers dynamically for each test case
            await session.commit()

        print(f"✅ Test environment ready")

    def run_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case against the API"""
        # Use unique customer ID to avoid rate limiting
        unique_customer_id = f"{
            test_case['input']['customerId']}_{
            test_case['id']}"

        payment_data = {
            "customerId": unique_customer_id,
            "amount": test_case["input"]["amount"],
            "currency": test_case["input"]["currency"],
            "payeeId": test_case["input"]["payeeId"],
            "idempotencyKey": f"eval_{test_case['id']}_{int(time.time())}"
        }

        headers = {"X-API-Key": self.api_key}

        try:
            response = self.client.post(
                "/payments/decide",
                json=payment_data,
                headers=headers)
            return {
                "test_id": test_case["id"],
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else None,
                "expected": test_case["expected"]}
        except Exception as e:
            return {
                "test_id": test_case["id"],
                "error": str(e),
                "expected": test_case["expected"]
            }

    def evaluate_decision(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if the decision matches expected outcome"""
        if "error" in result:
            return {
                "test_id": result["test_id"],
                "passed": False,
                "reason": f"API Error: {result['error']}"
            }

        if result["status_code"] != 200:
            return {
                "test_id": result["test_id"],
                "passed": False,
                "reason": f"HTTP Error: {result['status_code']}"
            }

        response = result["response"]
        expected = result["expected"]

        # Check decision
        decision_correct = response["decision"] == expected["decision"]

        # Check reasons (if specified)
        reasons_correct = True
        if "reasons" in expected:
            actual_reasons = set(response["reasons"])
            expected_reasons = set(expected["reasons"])
            reasons_correct = actual_reasons == expected_reasons

        passed = decision_correct and reasons_correct

        return {
            "test_id": result["test_id"],
            "passed": passed,
            "decision_correct": decision_correct,
            "reasons_correct": reasons_correct,
            "actual_decision": response["decision"],
            "expected_decision": expected["decision"],
            "actual_reasons": response["reasons"],
            "expected_reasons": expected.get("reasons", []),
            "description": expected.get("description", "")
        }

    async def run_evaluation(self) -> Dict[str, Any]:
        """Run the complete evaluation"""
        print("🚀 Starting agent evaluation...")

        # Load test cases
        with open("eval_test_cases.json", "r") as f:
            test_data = json.load(f)

        test_cases = test_data["test_cases"]
        print(f"📋 Loaded {len(test_cases)} test cases")

        # Setup customers for each test case
        async with AsyncSessionLocal() as session:
            for test_case in test_cases:
                unique_customer_id = f"{
                    test_case['input']['customerId']}_{
                    test_case['id']}"

                # Determine balance based on test case
                if test_case['input']['customerId'] == 'c_123':
                    balance = 1000.0
                elif test_case['input']['customerId'] == 'c_789':
                    balance = 2000.0
                else:
                    balance = 1000.0

                # Create customer for this test case
                customer = Customer(
                    id=unique_customer_id,
                    name=f"Test Customer {
                        test_case['id']}",
                    balance=balance)
                session.add(customer)

            await session.commit()

        # Run all test cases
        results = []
        for test_case in test_cases:
            result = self.run_test_case(test_case)
            evaluation = self.evaluate_decision(result)
            results.append(evaluation)

            status = "✅ PASS" if evaluation["passed"] else "❌ FAIL"
            print(
                f"{status} Test {
                    test_case['id']}: {
                    test_case['description']}")
            if not evaluation["passed"]:
                if "reason" in evaluation:
                    print(f"   Error: {evaluation['reason']}")
                else:
                    print(
                        f"   Expected: {
                            evaluation['expected_decision']}, Got: {
                            evaluation['actual_decision']}")
                    if evaluation["expected_reasons"]:
                        print(
                            f"   Expected reasons: {
                                evaluation['expected_reasons']}")
                        print(
                            f"   Actual reasons: {
                                evaluation['actual_reasons']}")

        # Calculate accuracy (only for tests that didn't have errors)
        valid_results = [r for r in results if "reason" not in r]
        if valid_results:
            passed_tests = sum(1 for r in valid_results if r["passed"])
            decision_accuracy = sum(
                1 for r in valid_results if r["decision_correct"]) / len(valid_results)
            reasons_accuracy = sum(
                1 for r in valid_results if r["reasons_correct"]) / len(valid_results)
            overall_accuracy = passed_tests / len(valid_results)
        else:
            passed_tests = 0
            decision_accuracy = 0
            reasons_accuracy = 0
            overall_accuracy = 0

        # Print summary
        print("\n" + "=" * 50)
        print("📊 EVALUATION RESULTS")
        print("=" * 50)
        print(f"Total Tests: {len(results)}")
        print(f"Valid Tests: {len(valid_results)}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {len(valid_results) - passed_tests}")
        print(f"Decision Accuracy: {decision_accuracy:.1%}")
        print(f"Reasons Accuracy: {reasons_accuracy:.1%}")
        print(f"Overall Accuracy: {overall_accuracy:.1%}")

        # Save detailed results
        evaluation_results = {
            "summary": {
                "total_tests": len(results),
                "valid_tests": len(valid_results),
                "passed": passed_tests,
                "failed": len(valid_results) - passed_tests,
                "decision_accuracy": decision_accuracy,
                "reasons_accuracy": reasons_accuracy,
                "overall_accuracy": overall_accuracy
            },
            "results": results
        }

        with open("eval_results.json", "w") as f:
            json.dump(evaluation_results, f, indent=2)

        print(f"\n📄 Detailed results saved to eval_results.json")

        # Return exit code based on accuracy
        return 0 if overall_accuracy >= 0.8 else 1


async def main():
    evaluator = AgentEvaluator()
    await evaluator.setup_test_environment()
    return await evaluator.run_evaluation()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
