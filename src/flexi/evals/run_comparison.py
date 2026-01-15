import json
import os
import time
import argparse
from datetime import datetime
from flexi.config.settings import settings
from flexi.evals.runner import EvaluationRunner

class ComparativeRunner:
    """
    Runs a comparison between two architectural regimes:
    1. Baseline (Standard Roles only)
    2. Experimental (Custom Roles allowed)
    """
    def __init__(self, suite: str = "quick"):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        regime = "open" if settings.USE_OPENSOURCE_MODELS else "closed"
        self.base_results_dir = os.path.join(project_root, "eval_results", "comparative", f"{self.timestamp}_{regime}")
        os.makedirs(self.base_results_dir, exist_ok=True)
        
        if suite == "comprehensive":
            self.questions_path = os.path.join(os.path.dirname(__file__), "test_questions/tier2_questions.json")
        else:
            self.questions_path = os.path.join(os.path.dirname(__file__), "test_questions/tier1_questions.json")
            
    def _run_eval(self, allow_custom: bool, label: str):
        print(f"\n🚀 Starting {label} Eval (allow_custom_roles={allow_custom})...")
        
        # Override settings for this run
        settings.ARCHITECT_ALLOW_CUSTOM_ROLES = allow_custom
        
        subfolder = f"comparative/{self.timestamp}_{'open' if settings.USE_OPENSOURCE_MODELS else 'closed'}/{label.lower()}"
        
        runner = EvaluationRunner(self.questions_path, subfolder)
        results = runner.run()
        
        # Load the summary created by runner.run()
        summary_path = os.path.join(runner.results_dir, "summary.json")
        
        if os.path.exists(summary_path):
            with open(summary_path, "r") as f:
                return json.load(f)
        return None

    def run_comparison(self):
        # Store original setting
        original_setting = settings.ARCHITECT_ALLOW_CUSTOM_ROLES
        
        try:
            # 1. Run Baseline (Strict)
            baseline_results = self._run_eval(False, "BASELINE")
            
            # 2. Run Experimental (Flexible)
            experimental_results = self._run_eval(True, "EXPERIMENTAL")
            
            if not baseline_results or not experimental_results:
                print("❌ Comparison failed due to missing results.")
                return

            # 3. Generate Comparative Report
            report = self._generate_report(baseline_results, experimental_results)
            
            report_path = os.path.join(self.base_results_dir, "comparison_report.md")
            
            with open(report_path, "w") as f:
                f.write(report)
                
            print(f"\n📊 Comparative Report generated at: {report_path}")
            print("\n" + "="*60)
            print(report)
            print("="*60)
        finally:
            # Restore original setting
            settings.ARCHITECT_ALLOW_CUSTOM_ROLES = original_setting

    def _generate_report(self, baseline, experimental):
        regime = "Open Source" if settings.USE_OPENSOURCE_MODELS else "Closed Source"
        lines = []
        lines.append(f"# Comparative Research Evaluation Report ({regime})")
        lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Model Regime: **{regime}**")
        regime_slug = "open" if settings.USE_OPENSOURCE_MODELS else "closed"
        lines.append(f"Run Directory: `eval_results/comparative/{self.timestamp}_{regime_slug}/`")
        lines.append("\n## Summary Metrics")
        
        table = [
            "| Metric | Baseline (Strict) | Experimental (Custom) | Delta |",
            "| :--- | :--- | :--- | :--- |"
        ]
        
        b_pass = baseline.get("pass_rate", 0)
        e_pass = experimental.get("pass_rate", 0)
        table.append(f"| Pass Rate | {b_pass:.1f}% | {e_pass:.1f}% | {e_pass - b_pass:+.1f}% |")
        
        # Aggregate scores
        def get_avg(results, metric):
            scores = [r.get("metrics", {}).get(metric, 0) for r in results if r.get("metrics")]
            return sum(scores) / len(scores) if scores else 0

        b_results = baseline.get("results", [])
        e_results = experimental.get("results", [])

        for metric in ["clarity", "citation", "reasoning"]:
            b_avg = get_avg(b_results, metric)
            e_avg = get_avg(e_results, metric)
            table.append(f"| Avg {metric.capitalize()} | {b_avg:.2f}/5 | {e_avg:.2f}/5 | {e_avg - b_avg:+.2f} |")

        b_cost = baseline.get("total_cost", 0)
        e_cost = experimental.get("total_cost", 0)
        cost_delta_pct = ((e_cost - b_cost) / b_cost * 100) if b_cost > 0 else 0
        table.append(f"| Total Cost | ${b_cost:.4f} | ${e_cost:.4f} | {cost_delta_pct:+.1f}% |")
        
        lines.extend(table)
        
        lines.append("\n## Per-Question Breakdown")
        lines.append("*Notation: (C: Clarity, R: Reasoning, T: Citation)*")
        q_table = [
            "| Question | Baseline | Experimental | Result |",
            "| :--- | :---: | :---: | :--- |"
        ]
        
        b_map = {r["id"]: r for r in b_results if "id" in r}
        e_map = {r["id"]: r for r in e_results if "id" in r}
        
        all_ids = sorted(list(set(b_map.keys()) | set(e_map.keys())))
        
        for qid in all_ids:
            br = b_map.get(qid, {})
            er = e_map.get(qid, {})
            
            b_passed = "✅" if "PASS" in br.get("status", "") else "❌"
            e_passed = "✅" if "PASS" in er.get("status", "") else "❌"
            
            # Show metrics
            def fmt_metrics(r):
                m = r.get('metrics', {})
                return f"(C:{m.get('clarity') or '-'}, R:{m.get('reasoning') or '-'}, T:{m.get('citation') or '-'})"

            b_info = f"{b_passed} {fmt_metrics(br)}"
            e_info = f"{e_passed} {fmt_metrics(er)}"
            
            comparison = ""
            if b_passed == "✅" and e_passed == "✅":
                cost_diff = er.get("metrics", {}).get("cost", 0) - br.get("metrics", {}).get("cost", 0)
                comparison = f"Cost delta: ${cost_diff:+.4f}"
            elif b_passed == "❌" and e_passed == "✅":
                comparison = "🟢 Experimental Fixed Failure"
            elif b_passed == "✅" and e_passed == "❌":
                comparison = "🔴 Experimental Regressed"
            
            q_table.append(f"| {br.get('question', qid)} | {b_info} | {e_info} | {comparison} |")
            
        lines.extend(q_table)
        
        lines.append("\n## Analysis")
        if e_pass > b_pass:
            lines.append("- **Quality**: Custom specialist roles improved completion rates.")
        elif e_pass < b_pass:
            lines.append("- **Reliability Warning**: Custom roles introduced regressions.")
        else:
            lines.append("- **Quality**: Completion rate remained stable.")
            
        if e_cost > b_cost:
            lines.append(f"- **Efficiency**: Experimental mode was {cost_delta_pct:.1f}% more expensive.")
        else:
            lines.append("- **Efficiency**: Experimental mode reduced overall research costs.")
            
        return "\n".join(lines)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run comparative evaluation between Baseline and Experimental regimes.")
    parser.add_argument("--suite", type=str, choices=["quick", "comprehensive"], default="quick",
                        help="The test suite to run (quick or comprehensive).")
    args = parser.parse_args()
    
    runner = ComparativeRunner(suite=args.suite)
    runner.run_comparison()
