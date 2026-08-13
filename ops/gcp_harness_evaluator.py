"""
GCP Cloud Run Harness Evaluator & Cost Assessment Engine
Smart Nurse Call (SNC) System - Hybrid Cloud Architecture
"""

import urllib.request
import urllib.parse
import json
import time
import sys

# Force UTF-8 stdout if possible
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CLOUD_RUN_URL = "https://snc-cloud-backend-59781590359.asia-southeast1.run.app"

class GCPHarnessEvaluator:
    def __init__(self, target_url=CLOUD_RUN_URL):
        self.target_url = target_url
        self.latencies = []
        self.results = {}

    def test_endpoint(self, path="", method="GET", data=None):
        url = f"{self.target_url}{path}"
        req = urllib.request.Request(url, method=method)
        if data:
            req.add_header('Content-Type', 'application/json')
            body = json.dumps(data).encode('utf-8')
        else:
            body = None

        start_time = time.time()
        try:
            with urllib.request.urlopen(req, data=body, timeout=10) as response:
                latency_ms = (time.time() - start_time) * 1000
                res_body = response.read().decode('utf-8')
                status_code = response.status
                return {
                    "success": True,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "data": res_body
                }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": str(e),
                "latency_ms": latency_ms
            }

    def run_harness_evaluation_loop(self, iterations=10):
        print("================================================================")
        print("CLOSED-LOOP HARNESS EVALUATION: GCP CLOUD RUN ENDPOINT")
        print(f"Target: {self.target_url}")
        print("================================================================")

        success_count = 0

        print("\n[Phase 1] Closed-Loop Latency & Health Probing...")
        for i in range(1, iterations + 1):
            res_health = self.test_endpoint("/health")
            res_root = self.test_endpoint("/")
            
            if res_health["success"] and res_root["success"]:
                success_count += 1
                avg_lat = (res_health["latency_ms"] + res_root["latency_ms"]) / 2
                self.latencies.append(avg_lat)
                print(f"  Loop {i:02d}: PASSED | Health Latency: {res_health['latency_ms']:.2f}ms | Root Latency: {res_root['latency_ms']:.2f}ms")
            else:
                err_msg = res_health.get('error') or res_root.get('error')
                print(f"  Loop {i:02d}: FAILED | {err_msg}")
            time.sleep(0.2)

        if self.latencies:
            sorted_lat = sorted(self.latencies)
            p50 = sorted_lat[int(len(sorted_lat) * 0.50)]
            p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if len(sorted_lat) > 1 else sorted_lat[-1]
            avg_lat = sum(sorted_lat) / len(sorted_lat)
            reliability = (success_count / iterations) * 100

            self.results["latency"] = {
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "avg_ms": round(avg_lat, 2),
                "reliability_percent": reliability
            }

            print("\nPerformance Summary:")
            print(f"  - Reliability Rate  : {reliability:.1f}%")
            print(f"  - Latency (p50)     : {p50:.2f} ms")
            print(f"  - Latency (p95)     : {p95:.2f} ms")
            print(f"  - Average Latency   : {avg_lat:.2f} ms")

    def calculate_gcp_cost_model(self):
        print("\n================================================================")
        print("GCP CLOUD RUN COST EVALUATION & LEDGER MODEL")
        print("================================================================")
        
        FREE_REQUESTS = 2_000_000 # 2 Million free requests/month
        FREE_VCPU_SEC = 180_000  # 180,000 vCPU-seconds free/month
        FREE_MEM_GB_SEC = 360_000 # 360,000 GB-seconds free/month
        
        COST_PER_MILLION_REQ = 0.40 # $0.40 per 1M requests
        COST_PER_VCPU_SEC = 0.00002400 # $0.000024 per vCPU-sec
        COST_PER_GB_SEC = 0.00000250   # $0.0000025 per GB-sec
        
        scenarios = [
            {"name": "Scenario A: Small Clinic / Ward (30 Rooms)", "monthly_calls": 15_000, "avg_duration_sec": 0.2, "vcpu": 1, "mem_gb": 0.5},
            {"name": "Scenario B: Medium Hospital Ward (100 Rooms)", "monthly_calls": 300_000, "avg_duration_sec": 0.2, "vcpu": 1, "mem_gb": 0.5},
            {"name": "Scenario C: Large Hospital Network (1,000 Rooms)", "monthly_calls": 3_000_000, "avg_duration_sec": 0.2, "vcpu": 1, "mem_gb": 0.5}
        ]

        cost_summary = []

        for sc in scenarios:
            reqs = sc["monthly_calls"]
            dur = sc["avg_duration_sec"]
            vcpu_sec = reqs * dur * sc["vcpu"]
            mem_gb_sec = reqs * dur * sc["mem_gb"]

            billable_reqs = max(0, reqs - FREE_REQUESTS)
            billable_vcpu = max(0, vcpu_sec - FREE_VCPU_SEC)
            billable_mem = max(0, mem_gb_sec - FREE_MEM_GB_SEC)

            cost_req = (billable_reqs / 1_000_000) * COST_PER_MILLION_REQ
            cost_vcpu = billable_vcpu * COST_PER_VCPU_SEC
            cost_mem = billable_mem * COST_PER_GB_SEC

            total_usd = cost_req + cost_vcpu + cost_mem
            total_thb = total_usd * 35.5

            sc_res = {
                "scenario": sc["name"],
                "monthly_calls": reqs,
                "billable_calls": billable_reqs,
                "total_cost_usd": round(total_usd, 2),
                "total_cost_thb": round(total_thb, 2),
                "is_free_tier": total_usd == 0
            }
            cost_summary.append(sc_res)

            print(f"\n* {sc['name']}:")
            print(f"  - Call Requests/Month : {reqs:,} calls")
            print(f"  - vCPU Usage          : {vcpu_sec:,.1f} vCPU-seconds")
            print(f"  - Memory Usage        : {mem_gb_sec:,.1f} GB-seconds")
            if total_usd == 0:
                print("  - Estimated Monthly Cost: FREE (100% Covered by GCP Free Tier)")
            else:
                print(f"  - Estimated Monthly Cost: ${total_usd:.2f} USD (~{total_thb:.2f} THB/month)")

        self.results["cost_model"] = cost_summary
        
        # Save evaluation result to json
        with open("ops/gcp_harness_eval_report.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print("\nSaved evaluation report to ops/gcp_harness_eval_report.json")

        return cost_summary

if __name__ == "__main__":
    evaluator = GCPHarnessEvaluator()
    evaluator.run_harness_evaluation_loop(iterations=10)
    evaluator.calculate_gcp_cost_model()
