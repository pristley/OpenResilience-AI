"""
Experiment Template for Chaos Engineering

Copy this file and customize for your specific failure scenario.

Usage:
    python run.py --dry-run              # Show what would happen
    python run.py --env=staging          # Run in staging
    python run.py --env=staging --verbose # Verbose output
"""

import argparse
import logging
import time
import json
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class ChaosExperiment:
    """Base class for chaos experiments"""

    def __init__(self, env: str, duration: int, blast_radius: float, verbose: bool = False):
        self.env = env
        self.duration = duration
        self.blast_radius = blast_radius
        self.verbose = verbose
        self.start_time = None
        self.end_time = None
        self.results = {}

        # Setup logging
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        self.logger.info("Received interrupt signal, cleaning up...")
        self.cleanup()
        sys.exit(0)

    def check_prerequisites(self) -> bool:
        """
        Verify all prerequisites are met before running.
        
        Returns:
            True if all prerequisites met, False otherwise
        """
        self.logger.info("Checking prerequisites...")

        checks = [
            ("Environment accessible", self._check_environment),
            ("Dependencies installed", self._check_dependencies),
            ("Monitoring available", self._check_monitoring),
            ("Kill switch working", self._check_kill_switch),
        ]

        all_passed = True
        for check_name, check_func in checks:
            try:
                if check_func():
                    self.logger.info(f"✅ {check_name}")
                else:
                    self.logger.error(f"❌ {check_name}")
                    all_passed = False
            except Exception as e:
                self.logger.error(f"❌ {check_name}: {e}")
                all_passed = False

        return all_passed

    def _check_environment(self) -> bool:
        """Check if environment is accessible"""
        # TODO: Implement environment check
        # Example: curl health endpoint
        return True

    def _check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        # TODO: Implement dependency check
        # Example: import required libraries
        return True

    def _check_monitoring(self) -> bool:
        """Check if monitoring is accessible"""
        # TODO: Implement monitoring check
        # Example: connect to Prometheus
        return True

    def _check_kill_switch(self) -> bool:
        """Verify we can stop the experiment"""
        # TODO: Implement kill switch check
        return True

    def inject_failure(self) -> None:
        """Inject the chaos"""
        self.logger.info(f"Injecting failure for {self.duration} seconds...")
        self.logger.info(f"Blast radius: {self.blast_radius}%")
        
        # TODO: Implement failure injection
        # Examples:
        # - Kill pods in Kubernetes
        # - Add latency to network calls
        # - Corrupt database
        # - Inject errors in service
        pass

    def monitor_impact(self) -> Dict[str, Any]:
        """Monitor system impact while chaos is active"""
        self.logger.info("Monitoring system impact...")
        
        impact_metrics = {
            "timestamp": datetime.now().isoformat(),
            "error_rate": None,
            "latency_p99": None,
            "affected_users": None,
            "alerts": [],
        }

        # TODO: Implement monitoring
        # Examples:
        # - Query Prometheus for metrics
        # - Check logs for errors
        # - Query trace system
        # - Check alert system
        
        return impact_metrics

    def verify_detection(self) -> bool:
        """Verify that the system detected the failure"""
        self.logger.info("Verifying failure detection...")
        
        # TODO: Implement detection verification
        # Check:
        # - Did expected alerts fire?
        # - Are metrics showing anomalies?
        # - Do logs show error patterns?
        
        return True

    def wait_for_recovery(self) -> bool:
        """Wait for system to recover automatically"""
        self.logger.info("Waiting for automatic recovery...")
        
        timeout = 300  # 5 minutes
        start = time.time()
        
        while time.time() - start < timeout:
            if self._system_is_healthy():
                elapsed = time.time() - start
                self.logger.info(f"✅ System recovered in {elapsed:.1f} seconds")
                return True
            
            time.sleep(5)
        
        self.logger.error(f"❌ System did not recover within {timeout} seconds")
        return False

    def _system_is_healthy(self) -> bool:
        """Check if system is healthy"""
        # TODO: Implement health check
        # Examples:
        # - Query health endpoint
        # - Check error rate < baseline
        # - Check latency < baseline
        return True

    def cleanup(self) -> None:
        """Restore system to baseline"""
        self.logger.info("Cleaning up...")
        
        # TODO: Implement cleanup
        # Examples:
        # - Restore killed pods
        # - Remove added latency
        # - Restore database
        # - Remove error injection
        
        self.logger.info("✅ Cleanup complete")

    def generate_report(self) -> str:
        """Generate experiment report"""
        report = f"""
Chaos Experiment Report
======================

Environment: {self.env}
Start Time: {self.start_time}
End Time: {self.end_time}
Duration: {self.duration} seconds
Blast Radius: {self.blast_radius}%

Results:
--------
"""
        for key, value in self.results.items():
            report += f"{key}: {value}\n"

        return report

    def run(self, dry_run: bool = False) -> bool:
        """Run the experiment"""
        self.start_time = datetime.now()
        
        if dry_run:
            self.logger.info("DRY RUN MODE - No actual changes will be made")
            self.logger.info(f"Would inject failure for {self.duration} seconds")
            self.logger.info(f"Would affect {self.blast_radius}% of {self.env}")
            return True

        try:
            # Verify prerequisites
            if not self.check_prerequisites():
                self.logger.error("Prerequisites failed, aborting")
                return False

            # Inject failure
            self.inject_failure()
            
            # Monitor impact
            for i in range(self.duration):
                impact = self.monitor_impact()
                self.results[f"second_{i}"] = impact
                
                # Check for detection
                if i == 5:  # After 5 seconds
                    if not self.verify_detection():
                        self.logger.warning("Failure not detected as expected")
                
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Progress: {i+1}/{self.duration} seconds")
                
                time.sleep(1)

            # Wait for recovery
            recovery_success = self.wait_for_recovery()
            self.results["recovery_success"] = recovery_success

        except Exception as e:
            self.logger.error(f"Experiment failed with error: {e}", exc_info=True)
            return False
        finally:
            self.cleanup()
            self.end_time = datetime.now()

        # Generate and print report
        report = self.generate_report()
        self.logger.info(report)

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Chaos Engineering Experiment"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes"
    )
    
    parser.add_argument(
        "--env",
        default="staging",
        choices=["staging", "test", "production"],
        help="Target environment"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration of experiment in seconds (default: 60)"
    )
    
    parser.add_argument(
        "--blast-radius",
        type=float,
        default=5.0,
        help="Percentage of traffic/systems affected (default: 5%)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--check-prereqs",
        action="store_true",
        help="Check prerequisites and exit"
    )

    args = parser.parse_args()

    # Create experiment
    experiment = ChaosExperiment(
        env=args.env,
        duration=args.duration,
        blast_radius=args.blast_radius,
        verbose=args.verbose
    )

    # Just check prerequisites if requested
    if args.check_prereqs:
        success = experiment.check_prerequisites()
        sys.exit(0 if success else 1)

    # Run experiment
    success = experiment.run(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
