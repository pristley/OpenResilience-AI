#!/usr/bin/env python3
"""
Hallucination Injection and Detection Experiment for GenAI Models

This experiment demonstrates how LLM hallucinations are injected, detected,
and how resilience strategies mitigate their impact. It simulates realistic
scenarios where models generate factually incorrect outputs and validates
recovery mechanisms.

Usage:
    python hallucination_experiment.py --mode inject --scenario date_hallucination
    python hallucination_experiment.py --mode detect --source rag
    python hallucination_experiment.py --mode graceful_degrade --failure_mode all
    python hallucination_experiment.py --mode full_scenario --case_study support_chatbot
"""

import argparse
import json
import logging
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests


class HallucinationType(Enum):
    """Types of hallucinations that can be injected."""
    DATE = "date"
    NUMBER = "number"
    ENTITY = "entity"
    SCHEMA = "schema"
    CITATION = "citation"
    FACT = "fact"


@dataclass
class HallucinationMetric:
    """Metrics for hallucination detection and impact."""
    timestamp: str
    hallucination_type: str
    confidence_score: float
    factuality_score: float
    detection_method: str
    time_to_detect_ms: float
    was_detected: bool
    impact_severity: str  # low, medium, high, critical
    user_impact: str


class HallucinationInjector:
    """Injects various types of hallucinations into LLM outputs for chaos testing."""

    def __init__(self, log_level: str = "INFO"):
        """Initialize the hallucination injector.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.logger = self._setup_logger(log_level)
        self.injected_hallucinations: List[Dict[str, Any]] = []
        self.detection_metrics: List[HallucinationMetric] = []

    @staticmethod
    def _setup_logger(level: str) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, level.upper()))
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def inject_date_hallucination(self, text: str, severity: str = "medium") -> str:
        """Inject incorrect dates into text.

        Args:
            text: Original text
            severity: low (past year), medium (wrong month), high (wrong decade)

        Returns:
            Text with injected date hallucinations
        """
        self.logger.info(f"Injecting {severity} date hallucination")

        # Extract date patterns
        date_patterns = [
            r"\d{4}-\d{2}-\d{2}",  # 2024-01-15
            r"\d{1,2}/\d{1,2}/\d{4}",  # 01/15/2024
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        ]

        modified_text = text
        injection_record = {"type": "date", "severity": severity, "replacements": []}

        for pattern in date_patterns:
            matches = re.finditer(pattern, modified_text)
            for match in matches:
                original_date = match.group()
                try:
                    # Parse and modify the date
                    if severity == "low":
                        # Shift by 1 year
                        shift_days = random.randint(365, 730)
                    elif severity == "medium":
                        # Shift by 1-6 months
                        shift_days = random.randint(30, 180)
                    else:
                        # Shift by 1-10 years
                        shift_days = random.randint(365, 3650)

                    # Generate fake date
                    fake_date = (datetime.now() - timedelta(days=shift_days)).strftime(
                        "%Y-%m-%d"
                    )
                    modified_text = modified_text.replace(original_date, fake_date, 1)
                    injection_record["replacements"].append(
                        {"original": original_date, "injected": fake_date}
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to inject date: {e}")

        self.injected_hallucinations.append(injection_record)
        return modified_text

    def inject_number_hallucination(
        self, text: str, severity: str = "medium", multiplier_range: Tuple[float, float] = None
    ) -> str:
        """Inject incorrect numbers into text.

        Args:
            text: Original text
            severity: low (±10%), medium (±50%), high (×10 or ÷10)
            multiplier_range: Optional tuple for custom range

        Returns:
            Text with injected number hallucinations
        """
        self.logger.info(f"Injecting {severity} number hallucination")

        injection_record = {"type": "number", "severity": severity, "replacements": []}

        # Find all numbers in text
        number_pattern = r"\b\d+(?:\.\d+)?\b"
        modified_text = text

        for match in re.finditer(number_pattern, modified_text):
            original_number = match.group()
            try:
                num_value = float(original_number)

                # Determine multiplier based on severity
                if multiplier_range:
                    multiplier = random.uniform(multiplier_range[0], multiplier_range[1])
                elif severity == "low":
                    multiplier = random.uniform(0.9, 1.1)
                elif severity == "medium":
                    multiplier = random.uniform(0.5, 1.5)
                else:
                    multiplier = random.choice([10.0, 0.1])

                fake_number = str(int(num_value * multiplier) if "." not in original_number
                                 else round(num_value * multiplier, 2))

                modified_text = modified_text.replace(original_number, fake_number, 1)
                injection_record["replacements"].append(
                    {"original": original_number, "injected": fake_number}
                )
            except Exception as e:
                self.logger.warning(f"Failed to inject number {original_number}: {e}")

        self.injected_hallucinations.append(injection_record)
        return modified_text

    def inject_entity_hallucination(
        self, text: str, entity_type: str = "person"
    ) -> str:
        """Inject incorrect entity names (people, companies, places).

        Args:
            text: Original text
            entity_type: person, company, location

        Returns:
            Text with injected entity hallucinations
        """
        self.logger.info(f"Injecting {entity_type} entity hallucination")

        injection_record = {
            "type": "entity",
            "entity_type": entity_type,
            "replacements": [],
        }

        # Sample entity replacements
        entity_replacements = {
            "person": [
                ("John Smith", "Jane Doe"),
                ("Alice Johnson", "Bob Wilson"),
                ("Sarah Chen", "Michael Anderson"),
            ],
            "company": [
                ("Google", "Microsoft"),
                ("Amazon", "Apple"),
                ("Meta", "Tesla"),
            ],
            "location": [
                ("New York", "Los Angeles"),
                ("London", "Paris"),
                ("Tokyo", "Beijing"),
            ],
        }

        modified_text = text
        if entity_type in entity_replacements:
            for original, fake in entity_replacements[entity_type]:
                if original in modified_text:
                    modified_text = modified_text.replace(original, fake, 1)
                    injection_record["replacements"].append(
                        {"original": original, "injected": fake}
                    )

        self.injected_hallucinations.append(injection_record)
        return modified_text

    def inject_schema_violation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inject schema violations (missing required fields, type mismatches).

        Args:
            data: Original data structure

        Returns:
            Data with schema violations
        """
        self.logger.info("Injecting schema violation")

        injection_record = {"type": "schema", "violations": []}
        modified_data = dict(data)

        # Inject schema violations
        if "price" in modified_data:
            original_price = modified_data["price"]
            modified_data["price"] = "not_a_number"  # Type mismatch
            injection_record["violations"].append(
                {"field": "price", "violation": "type_mismatch", "original": original_price}
            )

        if "count" in modified_data:
            modified_data["count"] = None  # Null violation for required field
            injection_record["violations"].append(
                {"field": "count", "violation": "null_violation"}
            )

        self.injected_hallucinations.append(injection_record)
        return modified_data

    def test_hallucination_detection(
        self, text: str, expected_hallucination: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """Test detection of hallucinations in text.

        Args:
            text: Text to analyze
            expected_hallucination: Whether hallucination is expected

        Returns:
            Tuple of (detection_result, detection_details)
        """
        self.logger.info("Testing hallucination detection")

        start_time = time.time() * 1000  # milliseconds

        detection_result = {
            "text": text,
            "detected_hallucination": False,
            "confidence_score": 0.0,
            "factuality_score": 0.0,
            "detection_time_ms": 0,
            "detection_methods_used": [],
            "issues_found": [],
        }

        # Simple heuristic-based detection
        # In production, use external validators or specialized models
        
        # Check for suspicious patterns
        suspicious_patterns = [
            (r"exactly \d{4} years? ago", "Vague temporal reference"),
            (r"According to our records from \d{2,4}(?!-)", "Suspicious date reference"),
            (r"\b(?:approximately|roughly|around|about) \d{1,3}% (?:increase|decrease)",
             "Vague percentage"),
        ]

        issues_found = []
        for pattern, issue_type in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues_found.append(issue_type)
                detection_result["detection_methods_used"].append("pattern_matching")

        # External validation (would call actual validator in production)
        try:
            external_check = self._external_validator_check(text)
            if external_check:
                issues_found.extend(external_check["issues"])
                detection_result["detection_methods_used"].append("external_validator")
        except Exception as e:
            self.logger.warning(f"External validation failed: {e}")

        detection_result["issues_found"] = issues_found
        detection_result["detected_hallucination"] = len(issues_found) > 0
        detection_result["confidence_score"] = len(issues_found) / max(1, len(issues_found) + 1)
        detection_result["detection_time_ms"] = time.time() * 1000 - start_time

        # Record metric
        metric = HallucinationMetric(
            timestamp=datetime.now().isoformat(),
            hallucination_type="general",
            confidence_score=detection_result["confidence_score"],
            factuality_score=1.0 - detection_result["confidence_score"],
            detection_method=",".join(detection_result["detection_methods_used"]),
            time_to_detect_ms=detection_result["detection_time_ms"],
            was_detected=detection_result["detected_hallucination"],
            impact_severity="high" if detection_result["confidence_score"] > 0.7 else "low",
            user_impact="Misinformation delivered" if detection_result["detected_hallucination"] else "None",
        )
        self.detection_metrics.append(metric)

        return detection_result["detected_hallucination"], detection_result

    def _external_validator_check(self, text: str) -> Optional[Dict[str, Any]]:
        """Call external validator service (e.g., fact-checking API).

        Args:
            text: Text to validate

        Returns:
            Validation results or None if service unavailable
        """
        try:
            response = requests.post(
                "http://localhost:8000/validate",
                json={"text": text},
                timeout=2,
            )
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException:
            self.logger.debug("External validator unavailable")
        return None

    def test_graceful_degradation(
        self,
        text: str,
        confidence_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """Test graceful degradation when hallucinations detected.

        Args:
            text: Text to evaluate
            confidence_threshold: Threshold above which to degrade

        Returns:
            Degradation strategy and result
        """
        self.logger.info("Testing graceful degradation")

        detected, detection_details = self.test_hallucination_detection(text)

        strategy_result = {
            "original_text": text,
            "hallucination_detected": detected,
            "confidence_score": detection_details["confidence_score"],
            "degradation_applied": False,
            "degradation_strategy": None,
            "final_response": text,
        }

        if detected and detection_details["confidence_score"] > confidence_threshold:
            strategy_result["degradation_applied"] = True

            # Apply degradation strategies
            if detection_details["confidence_score"] > 0.9:
                # High confidence hallucination: refuse to answer
                strategy_result["degradation_strategy"] = "refuse"
                strategy_result["final_response"] = (
                    "I'm not confident in this information. Please verify with "
                    "authoritative sources."
                )
            elif detection_details["confidence_score"] > 0.7:
                # Medium confidence: add disclaimer
                strategy_result["degradation_strategy"] = "disclaimer"
                strategy_result["final_response"] = (
                    f"{text}\n\n[DISCLAIMER: This response may contain inaccuracies. "
                    "Please verify critical information independently.]"
                )
            else:
                # Low confidence: request human review
                strategy_result["degradation_strategy"] = "escalate"
                strategy_result["final_response"] = (
                    "[HUMAN REVIEW REQUIRED] This response requires verification."
                )

        return strategy_result

    def get_detection_metrics_summary(self) -> Dict[str, Any]:
        """Get summary statistics of all detection metrics.

        Returns:
            Summary statistics
        """
        if not self.detection_metrics:
            return {"total_tests": 0, "summary": "No metrics recorded"}

        metrics = self.detection_metrics
        detected_count = sum(1 for m in metrics if m.was_detected)
        avg_detection_time = sum(m.time_to_detect_ms for m in metrics) / len(metrics)

        return {
            "total_tests": len(metrics),
            "hallucinations_detected": detected_count,
            "detection_rate": detected_count / len(metrics),
            "avg_detection_time_ms": avg_detection_time,
            "avg_confidence_score": sum(m.confidence_score for m in metrics) / len(metrics),
            "severity_distribution": {
                "low": sum(1 for m in metrics if m.impact_severity == "low"),
                "medium": sum(1 for m in metrics if m.impact_severity == "medium"),
                "high": sum(1 for m in metrics if m.impact_severity == "high"),
                "critical": sum(1 for m in metrics if m.impact_severity == "critical"),
            },
        }


def run_scenario_date_hallucination():
    """Run date hallucination injection scenario."""
    print("\n=== Scenario: Date Hallucination ===\n")

    injector = HallucinationInjector()

    text = (
        "The COVID-19 pandemic started in December 2019 in Wuhan, China. "
        "The first vaccine was approved on 2020-12-11. "
        "By January 1, 2021, vaccination campaigns had begun globally."
    )

    print(f"Original text:\n{text}\n")

    # Inject hallucinations with different severities
    for severity in ["low", "medium", "high"]:
        hallucinated = injector.inject_date_hallucination(text, severity)
        print(f"After {severity} severity injection:\n{hallucinated}\n")

        # Test detection
        detected, details = injector.test_hallucination_detection(hallucinated)
        print(f"Detection result: {detected}")
        print(f"Confidence: {details['confidence_score']:.2f}\n")


def run_scenario_number_hallucination():
    """Run number hallucination injection scenario."""
    print("\n=== Scenario: Number Hallucination ===\n")

    injector = HallucinationInjector()

    text = (
        "Q4 revenue increased by 25% to $1.5 billion. "
        "Customer acquisition cost decreased from $50 to $40. "
        "Churn rate improved from 5% to 3%."
    )

    print(f"Original text:\n{text}\n")

    hallucinated = injector.inject_number_hallucination(text, severity="high")
    print(f"After high severity injection:\n{hallucinated}\n")

    detected, details = injector.test_hallucination_detection(hallucinated)
    print(f"Detection result: {detected}")
    print(f"Issues found: {details['issues_found']}\n")


def run_scenario_entity_hallucination():
    """Run entity hallucination injection scenario."""
    print("\n=== Scenario: Entity Hallucination ===\n")

    injector = HallucinationInjector()

    text = (
        "According to research by Alice Johnson at Google, machine learning models "
        "can now achieve 95% accuracy on image classification tasks. "
        "The study was conducted in London and published last year."
    )

    print(f"Original text:\n{text}\n")

    hallucinated = injector.inject_entity_hallucination(text, "person")
    print(f"After person substitution:\n{hallucinated}\n")


def run_scenario_graceful_degradation():
    """Run graceful degradation scenario."""
    print("\n=== Scenario: Graceful Degradation ===\n")

    injector = HallucinationInjector()

    test_texts = [
        "The Earth orbits the Sun, completing one orbit every 365.25 days.",
        "According to our records from 1985, the stock market crashed yesterday.",
        "The current CEO, Jane Doe, joined the company exactly 50 years ago.",
    ]

    for text in test_texts:
        print(f"Input: {text}")
        result = injector.test_graceful_degradation(text)
        print(f"Hallucination detected: {result['hallucination_detected']}")
        print(f"Strategy applied: {result['degradation_strategy']}")
        print(f"Final response: {result['final_response']}\n")


def run_full_scenario():
    """Run comprehensive scenario with multiple stages."""
    print("\n=== Full Scenario: Support Chatbot Hallucination Impact ===\n")

    injector = HallucinationInjector()

    # Stage 1: Normal operation
    print("Stage 1: Normal Operation")
    normal_response = (
        "To reset your password, go to Settings > Security > Change Password. "
        "This was updated on 2024-01-15."
    )
    print(f"Response: {normal_response}\n")

    # Stage 2: Hallucination injection
    print("Stage 2: Hallucination Injection")
    hallucinated = injector.inject_date_hallucination(
        normal_response, severity="high"
    )
    hallucinated = injector.inject_number_hallucination(hallucinated, severity="medium")
    print(f"Response: {hallucinated}\n")

    # Stage 3: Detection
    print("Stage 3: Detection")
    detected, details = injector.test_hallucination_detection(hallucinated)
    print(f"Hallucination detected: {detected}")
    print(f"Confidence: {details['confidence_score']:.2f}\n")

    # Stage 4: Graceful degradation
    print("Stage 4: Graceful Degradation")
    degraded = injector.test_graceful_degradation(hallucinated)
    print(f"Original: {degraded['original_text']}")
    print(f"Degradation strategy: {degraded['degradation_strategy']}")
    print(f"Final response: {degraded['final_response']}\n")

    # Stage 5: Metrics
    print("Stage 5: Detection Metrics Summary")
    metrics = injector.get_detection_metrics_summary()
    print(json.dumps(metrics, indent=2))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Hallucination Injection and Detection Experiment"
    )
    parser.add_argument(
        "--mode",
        choices=["inject", "detect", "graceful_degrade", "full_scenario"],
        default="full_scenario",
        help="Experiment mode",
    )
    parser.add_argument(
        "--scenario",
        choices=["date_hallucination", "number_hallucination", "entity_hallucination"],
        default="date_hallucination",
        help="Scenario to run",
    )

    args = parser.parse_args()

    if args.mode == "inject":
        if args.scenario == "date_hallucination":
            run_scenario_date_hallucination()
        elif args.scenario == "number_hallucination":
            run_scenario_number_hallucination()
        elif args.scenario == "entity_hallucination":
            run_scenario_entity_hallucination()

    elif args.mode == "graceful_degrade":
        run_scenario_graceful_degradation()

    else:  # full_scenario
        run_full_scenario()


if __name__ == "__main__":
    main()
