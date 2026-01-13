import json
import time
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from flexi.agents.architect import create_architect
from flexi.agents.graph_builder import DynamicResearchSystemBuilder
from flexi.evals.metrics import calculate_all_metrics
from flexi.evals.judges import ReportJudge
from flexi.core.utils import slugify_question

class EvaluationRunner:
    """Unified engine for running research evaluations."""
    
    def __init__(self, questions_path: str, results_subfolder: str):
        self.questions_path = questions_path
        with open(self.questions_path, "r") as f:
            self.test_cases = json.load(f)
        
        self.judge = ReportJudge()
        self.results_dir = self._setup_results_dir(results_subfolder)
        
    def _setup_results_dir(self, subfolder: str) -> str:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        results_dir = os.path.join(project_root, "eval_results", subfolder)
        os.makedirs(results_dir, exist_ok=True)
        return results_dir

    def run(self) -> List[Dict[str, Any]]:
        print(f"\n{'='*60}")
        print(f"🚀 STARTING EVALUATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📂 Results: {self.results_dir}")
        print(f"{'='*60}")
        
        results = []
        total_cost = 0.0
        
        for case in self.test_cases:
            question = case["question"]
            print(f"\n[CASE {case['id']}] Question: {question}")
            
            start_time = time.time()
            
            # --- 1. Architect Design ---
            architect = create_architect()
            config = architect.design_system(question)
            
            # Log Plan
            print(f"  -> Architect Complexity: {config.complexity.upper()}")
            plan_preview = str(config.suggested_workflow[:3]) if config.suggested_workflow else "No specific plan"
            print(f"  -> Planned Steps: {plan_preview}...")
            
            # --- 2. Build and Run ---
            builder = DynamicResearchSystemBuilder(config)
            state = builder.run(question)
            elapsed = time.time() - start_time
            
            # --- 3. Extract Report (Robust Logic) ---
            findings = state.get("findings", {})
            report = self._extract_report(findings, config.complexity)
            
            # --- 4. Validation (Tools) ---
            tool_penalty, missing_tools = self._validate_tools(case, config)
            
            # --- 5. Judge ---
            print(f"  -> Judging report quality...")
            judgment = self.judge.evaluate(question, report, state)
            
            # Apply Tool Penalty (Enforce Architecture)
            if tool_penalty > 0 and judgment.get("clarity_score", 0) > 3:
                judgment["clarity_score"] = max(1, judgment["clarity_score"] - 1)
                judgment["justification"] += f" [PENALTY: Missing expected tools {missing_tools}]"
            
            # --- 6. Metrics ---
            cost = sum(s.get("cost", 0.0) for s in state.get("stats", []))
            if config.stats:
                cost += config.stats.get("cost", 0.0)
            total_cost += cost
            
            metrics = calculate_all_metrics(state, judgment)
            metrics["cost"] = round(cost, 4)
            metrics["duration"] = round(elapsed, 2)
            
            # Pass Decision: Clarity > 2 AND Valid Report
            has_report = len(report) > 50 and report != "No Report Generated"
            passed = metrics["clarity"] > 2 and has_report
            
            result = {
                "id": case["id"],
                "question": question,
                "status": "✅ PASS" if passed else "❌ FAIL",
                "metrics": metrics,
                "summary": judgment.get("justification")
            }
            results.append(result)
            
            print(f"  -> {result['status']} | Clarity: {metrics['clarity']}/5 | Cost: ${metrics['cost']} | Efficiency: {metrics['tool_efficiency']}/5")
            
            # --- 7. Save Artifacts ---
            self._save_case_artifacts(question, report, config, state, judgment, metrics)

        self._print_summary(results, total_cost)
        return results

    def _extract_report(self, findings: Dict[str, str], complexity: str) -> str:
        """Robust strategy to extract the final report from diverse agent outputs."""
        report = ""
        
        # Priority 1: Specific Final Output Roles
        if "writer" in findings:
            report = findings["writer"]
        elif "summarizer" in findings:
            report = findings["summarizer"]
        elif "responder" in findings:
            report = findings["responder"]
            
        # Priority 2: Fuzzy Match for Simple Tasks (e.g. 'responder_javascript')
        if not report:
            for key, content in findings.items():
                if "responder" in key or "researcher" in key:
                    report = content
                    break
        
        # Priority 3: Fallback to largest content
        if not report and findings:
            report = max(findings.values(), key=len)
            
        if not report:
            print(f"  ⚠️  WARNING: No report extracted. Keys found: {list(findings.keys())}")
            return "No Report Generated"
            
        return report

    def _validate_tools(self, case: Dict[str, Any], config: Any) -> tuple[float, List[str]]:
        """Check if architect equipped the tools required by the test case."""
        if "expected_tools" not in case:
            return 0.0, []
            
        expected = set(case["expected_tools"])
        planned_tools = set()
        for agent_conf in config.agents.values():
            planned_tools.update(agent_conf.tools)
        
        missing = expected - planned_tools
        if missing:
            print(f"  ⚠️  WARNING: Architect failed to equip expected tools: {missing}")
            return 0.5, list(missing)
            
        return 0.0, []

    def _save_case_artifacts(self, question: str, report: str, config: Any, state: Dict, judgment: Dict, metrics: Dict):
        slug = slugify_question(question)
        case_dir = os.path.join(self.results_dir, slug)
        os.makedirs(case_dir, exist_ok=True)
        
        with open(os.path.join(case_dir, "report.md"), "w") as f:
            f.write(report)
            
        trace_data = {
            "question": question,
            "metrics": metrics,
            "architect_config": config.to_dict() if hasattr(config, 'to_dict') else str(config),
            "state": {k: v for k, v in state.items() if k != 'llm'},
            "judgment": judgment
        }
        
        with open(os.path.join(case_dir, "trace.json"), "w") as f:
             # Default to str to handle non-serializable objects gracefully
            json.dump(trace_data, f, indent=2, default=str)

    def _print_summary(self, results: List[Dict], total_cost: float):
        passes = sum(1 for r in results if "PASS" in r["status"])
        pass_rate = (passes / len(results)) * 100 if results else 0
        
        print(f"\n{'='*60}")
        print(f"📊 SUMMARY")
        print(f"{'='*60}")
        print(f"Pass Rate: {pass_rate:.1f}% ({passes}/{len(results)})")
        print(f"Total Cost: ${total_cost:.4f}")
        print(f"{'='*60}\n")
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "pass_rate": pass_rate,
            "total_cost": total_cost,
            "results": results
        }
        with open(os.path.join(self.results_dir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
