import json
import os
import subprocess
import time
from datetime import datetime
from flexi.config.settings import settings

class ComparativeRunner:
    def __init__(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_results_dir = os.path.join(project_root, "eval_results", "comparative", self.timestamp)
        os.makedirs(self.base_results_dir, exist_ok=True)
        
    def _run_eval(self, allow_custom: bool, label: str):
        print(f"\n🚀 Running {label} Eval (allow_custom_roles={allow_custom})...")
        
        # We override settings at runtime for the duration of this process
        subfolder = f"comparative/{self.timestamp}/{label.lower()}"
        
        env = os.environ.copy()
        env["FLEXI_ARCHITECT_ALLOW_CUSTOM_ROLES"] = str(allow_custom)
        env["FLEXI_EVAL_SUBFOLDER"] = subfolder
        
        start_time = time.time()
        # Set PYTHONPATH to include src directory
        src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{src_path}:{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = src_path

        result = subprocess.run(
            ["python", "-m", "flexi.evals.quick_eval"],
            env=env,
            text=True
        )
        duration = time.time() - start_time
        
        if result.returncode != 0:
            print(f"❌ {label} Eval failed!")
            return None
            
        print(f"✅ {label} Eval finished in {duration:.2f}s")
        
        # Load the summary created by quick_eval (it will be in eval_results/{subfolder})
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        summary_path = os.path.join(project_root, "eval_results", subfolder, "quick_eval_summary.json")
        
        if os.path.exists(summary_path):
            with open(summary_path, "r") as f:
                return json.load(f)
        return None

    def run_comparison(self):
        # 1. Run Baseline
        baseline_results = self._run_eval(False, "BASELINE")
        
        # 2. Run Experimental
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

    def _generate_report(self, baseline, experimental):
        lines = []
        lines.append("# Comparative Research Evaluation Report")
        lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Run Directory: `eval_results/comparative/{self.timestamp}/`")
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
        table.append(f"| Total Cost | ${b_cost:.4f} | ${e_cost:.4f} | {((e_cost-b_cost)/b_cost)*100:+.1f}% if {b_cost} > 0 else 'N/A' |")
        
        lines.extend(table)
        
        lines.append("\n## Per-Question Breakdown")
        lines.append("*Notation: (C: Clarity, R: Reasoning, T: Citation)*")
        q_table = [
            "| Question | Baseline | Experimental | Result |",
            "| :--- | :---: | :---: | :--- |"
        ]
        
        b_map = {r["id"]: r for r in b_results}
        e_map = {r["id"]: r for r in e_results}
        
        all_ids = sorted(list(set(b_map.keys()) | set(e_map.keys())))
        
        for qid in all_ids:
            br = b_map.get(qid, {})
            er = e_map.get(qid, {})
            
            b_status = "✅" if br.get("completion") else "❌"
            e_status = "✅" if er.get("completion") else "❌"
            
            # Show full metric triple: (C, R, T)
            def fmt_metrics(r):
                m = r.get('metrics', {})
                return f"(C:{m.get('clarity') or '-'}, R:{m.get('reasoning') or '-'}, T:{m.get('citation') or '-'})"

            b_info = f"{b_status} {fmt_metrics(br)}"
            e_info = f"{e_status} {fmt_metrics(er)}"
            
            comparison = ""
            if b_status == "✅" and e_status == "✅":
                cost_diff = er.get("cost", 0) - br.get("cost", 0)
                comparison = f"Cost delta: ${cost_diff:+.4f}"
            elif b_status == "❌" and e_status == "✅":
                comparison = "🟢 Experimental Fixed Failure"
            elif b_status == "✅" and e_status == "❌":
                comparison = "🔴 Experimental Caused Failure"
            
            q_table.append(f"| {br.get('question', qid)} | {b_info} | {e_info} | {comparison} |")
            
        lines.extend(q_table)
        
        lines.append("\n## Analysis")
        if e_pass > b_pass:
            lines.append("- **Quality**: Custom specialist roles improved completion rates.")
        elif e_pass < b_pass:
            lines.append("- **Reliability Warning**: Custom roles introduced regressions or instability.")
        else:
            lines.append("- **Quality**: Completion rate remained stable across both regimes.")
            
        if e_cost > b_cost:
            lines.append(f"- **Efficiency**: Experimental mode was {((e_cost-b_cost)/b_cost)*100:.1f}% more expensive.")
        else:
            lines.append("- **Efficiency**: Experimental mode reduced overall research costs.")
            
        return "\n".join(lines)

if __name__ == "__main__":
    runner = ComparativeRunner()
    runner.run_comparison()
