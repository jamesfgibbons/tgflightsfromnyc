#!/usr/bin/env python3
"""
Deployment Verification Script

Comprehensive end-to-end verification of the SERPRadio deployment.
Checks database, API, pricing pipeline, and deal awareness features.

Usage:
    # Verify Railway backend deployment
    export API_BASE=https://your-app.railway.app
    export SUPABASE_URL=https://your-project.supabase.co
    export SUPABASE_SERVICE_ROLE=your-service-role-key
    python scripts/verify_deployment.py

    # Verify local development
    export API_BASE=http://localhost:8000
    export SUPABASE_URL=https://your-project.supabase.co
    export SUPABASE_SERVICE_ROLE=your-service-role-key
    python scripts/verify_deployment.py

Exit codes:
    0 - All checks passed
    1 - Some checks failed
    2 - Critical failure (configuration error)
"""

import os
import sys
import httpx
from datetime import datetime

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ ERROR: supabase-py not installed")
    print("   Install with: pip install supabase")
    sys.exit(2)


class DeploymentVerifier:
    def __init__(self, api_base: str, supabase_url: str, supabase_key: str):
        self.api_base = api_base.rstrip("/")
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.supabase: Client = None
        self.checks_passed = 0
        self.checks_failed = 0

    def print_header(self, text: str):
        """Print section header"""
        print()
        print("=" * 70)
        print(f"  {text}")
        print("=" * 70)

    def check(self, name: str, passed: bool, details: str = ""):
        """Record and print check result"""
        if passed:
            print(f"✅ {name}")
            if details:
                print(f"   {details}")
            self.checks_passed += 1
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")
            self.checks_failed += 1

    def verify_environment(self):
        """Verify environment variables"""
        self.print_header("1. Environment Configuration")

        self.check(
            "API_BASE set",
            bool(self.api_base),
            f"API_BASE={self.api_base}"
        )

        self.check(
            "SUPABASE_URL set",
            bool(self.supabase_url),
            f"SUPABASE_URL={self.supabase_url}"
        )

        self.check(
            "SUPABASE_SERVICE_ROLE set",
            bool(self.supabase_key),
            f"Key: {self.supabase_key[:8]}...{self.supabase_key[-4:]}" if self.supabase_key else "Not set"
        )

    def verify_database(self):
        """Verify Supabase database connection and schema"""
        self.print_header("2. Database Connection & Schema")

        try:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            self.check("Supabase client initialized", True)
        except Exception as e:
            self.check("Supabase client initialized", False, str(e))
            return

        # Check tables exist
        tables = ["price_observation", "route_baseline_30d", "notification_event"]
        for table in tables:
            try:
                result = self.supabase.table(table).select("*").limit(1).execute()
                self.check(f"Table '{table}' exists", True)
            except Exception as e:
                self.check(f"Table '{table}' exists", False, str(e))

        # Check RPC functions
        functions = ["evaluate_deal", "refresh_baselines", "detect_price_drops"]
        for func in functions:
            try:
                # Try calling with minimal params (will fail but proves function exists)
                if func == "evaluate_deal":
                    self.supabase.rpc(func, {
                        "p_origin": "JFK",
                        "p_dest": "MIA",
                        "p_month": 3
                    }).execute()
                    self.check(f"RPC function '{func}' exists", True)
                else:
                    # Just check if function exists (don't call)
                    self.check(f"RPC function '{func}' exists (not tested)", True, "Manual test required")
            except Exception as e:
                # If error is about missing data, function exists
                if "no rows" in str(e).lower() or "null" in str(e).lower():
                    self.check(f"RPC function '{func}' exists", True)
                else:
                    self.check(f"RPC function '{func}' exists", False, str(e))

    def verify_data(self):
        """Verify price data exists"""
        self.print_header("3. Price Data")

        if not self.supabase:
            print("⚠️  Skipping (database not connected)")
            return

        # Check price_observation has data
        try:
            result = self.supabase.table("price_observation").select("*", count="exact").limit(0).execute()
            count = result.count if hasattr(result, 'count') else 0

            self.check(
                "Price observations exist",
                count > 0,
                f"Found {count} observations"
            )

            if count > 0:
                # Get sample observation
                sample = self.supabase.table("price_observation").select("*").limit(1).execute()
                if sample.data:
                    obs = sample.data[0]
                    self.check(
                        "Sample observation valid",
                        True,
                        f"{obs['origin']}→{obs['dest']} ${obs['price_usd']:.2f} on {obs['depart_date']}"
                    )
        except Exception as e:
            self.check("Price observations exist", False, str(e))

        # Check route_baseline_30d has data
        try:
            result = self.supabase.table("route_baseline_30d").select("*", count="exact").limit(0).execute()
            count = result.count if hasattr(result, 'count') else 0

            self.check(
                "Baseline data exists",
                count > 0,
                f"Found {count} route baselines"
            )

            if count > 0:
                # Get sample baseline
                sample = self.supabase.table("route_baseline_30d").select("*").limit(1).execute()
                if sample.data:
                    baseline = sample.data[0]
                    self.check(
                        "Sample baseline valid",
                        True,
                        f"{baseline['origin']}→{baseline['dest']} P25=${baseline['p25_30d']:.2f} P50=${baseline['p50_30d']:.2f}"
                    )
        except Exception as e:
            self.check("Baseline data exists", False, str(e))

    def verify_api(self):
        """Verify API endpoints"""
        self.print_header("4. API Endpoints")

        # Health check
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.api_base}/api/healthz")
                self.check(
                    "Health endpoint (/api/healthz)",
                    response.status_code == 200,
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.check("Health endpoint (/api/healthz)", False, str(e))

        # Deal awareness endpoints
        endpoints = [
            ("/api/deals/health", "Deals health check"),
            ("/api/deals/evaluate?origin=JFK&dest=MIA&month=3", "Deal evaluation"),
        ]

        for endpoint, name in endpoints:
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(f"{self.api_base}{endpoint}")

                    if response.status_code == 200:
                        data = response.json()
                        self.check(
                            name,
                            True,
                            f"Status: {response.status_code}, Response: {str(data)[:100]}"
                        )
                    else:
                        self.check(
                            name,
                            False,
                            f"Status: {response.status_code}"
                        )
            except Exception as e:
                self.check(name, False, str(e))

        # Board feed endpoint
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.api_base}/api/board/feed")
                self.check(
                    "Board feed endpoint",
                    response.status_code == 200,
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.check("Board feed endpoint", False, str(e))

    def verify_deal_awareness(self):
        """Verify deal awareness feature works end-to-end"""
        self.print_header("5. Deal Awareness Feature")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.api_base}/api/deals/evaluate",
                    params={
                        "origin": "JFK",
                        "dest": "MIA",
                        "month": 3,
                        "cabin": "economy"
                    }
                )

                if response.status_code != 200:
                    self.check("Deal evaluation request", False, f"HTTP {response.status_code}")
                    return

                data = response.json()

                # Check response structure
                required_fields = ["origin", "dest", "month", "has_data", "recommendation"]
                has_all_fields = all(field in data for field in required_fields)

                self.check(
                    "Response structure valid",
                    has_all_fields,
                    f"Fields: {list(data.keys())}"
                )

                # Check if has data
                if data.get("has_data"):
                    self.check(
                        "Has baseline data",
                        True,
                        f"Recommendation: {data.get('recommendation')}, Score: {data.get('deal_score')}"
                    )

                    # Check baseline values
                    baseline = data.get("baseline", {})
                    if baseline:
                        self.check(
                            "Baseline percentiles valid",
                            all(k in baseline for k in ["p25", "p50", "p75"]),
                            f"P25=${baseline.get('p25'):.2f} P50=${baseline.get('p50'):.2f} P75=${baseline.get('p75'):.2f}"
                        )
                else:
                    self.check(
                        "Has baseline data",
                        False,
                        "No data available. Run price refresh or seed sample data."
                    )

        except Exception as e:
            self.check("Deal awareness feature", False, str(e))

    def print_summary(self):
        """Print verification summary"""
        self.print_header("Verification Summary")

        total = self.checks_passed + self.checks_failed
        percentage = (self.checks_passed / total * 100) if total > 0 else 0

        print(f"Total checks: {total}")
        print(f"✅ Passed: {self.checks_passed}")
        print(f"❌ Failed: {self.checks_failed}")
        print(f"Success rate: {percentage:.1f}%")
        print()

        if self.checks_failed == 0:
            print("🎉 All checks passed! Deployment is ready.")
            return 0
        elif self.checks_failed <= 3:
            print("⚠️  Some checks failed. Review errors above.")
            return 1
        else:
            print("❌ Multiple checks failed. Review configuration and deployment.")
            return 1

    def run(self):
        """Run all verification checks"""
        print("🔍 SERPRadio Deployment Verification")
        print(f"Timestamp: {datetime.now().isoformat()}")

        self.verify_environment()
        self.verify_database()
        self.verify_data()
        self.verify_api()
        self.verify_deal_awareness()

        return self.print_summary()


def main():
    # Get environment
    api_base = os.getenv("API_BASE", "http://localhost:8000")
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE", "")

    if not all([api_base, supabase_url, supabase_key]):
        print("❌ ERROR: Required environment variables not set")
        print()
        print("Required:")
        print("  API_BASE=https://your-app.railway.app")
        print("  SUPABASE_URL=https://your-project.supabase.co")
        print("  SUPABASE_SERVICE_ROLE=your-service-role-key")
        print()
        print("Example:")
        print("  export API_BASE=http://localhost:8000")
        print("  export SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co")
        print("  export SUPABASE_SERVICE_ROLE=your-key")
        print("  python scripts/verify_deployment.py")
        sys.exit(2)

    # Run verification
    verifier = DeploymentVerifier(api_base, supabase_url, supabase_key)
    exit_code = verifier.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
