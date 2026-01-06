import json
import time
import os
from datetime import datetime
from flexi.agents.architect import create_architect
from flexi.agents.graph_builder import DynamicResearchSystemBuilder
from flexi.evals.metrics import calculate_task_completion
from flexi.evals.judges import ReportJudge
from flexi.core.utils import slugify_question

class QuickEval:
    def __init__(self, results_subfolder: str = None):
        self.questions_path = os.path.join(os.path.dirname(__file__), "test_questions/tier1_questions.json")
        with open(self.questions_path, "r") as f:
            self.test_cases = json.load(f)
        self.judge = ReportJudge() # Upgraded to high-fidelity judge
        
        # Determine internal subfolder (env var > arg > default)
        subfolder = os.getenv("FLEXI_EVAL_SUBFOLDER", results_subfolder or "quick")
        
        # Move results out of src/ for project hygiene
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        self.results_dir = os.path.join(project_root, "eval_results", subfolder)
        os.makedirs(self.results_dir, exist_ok=True)
    
    def run(self):
        print(f"\n{'='*60}")
        print(f"🚀 STARTING QUICK EVAL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        results = []
        total_cost = 0.0
        
        for case in self.test_cases:
            question = case["question"]
            print(f"\n[CASE {case['id']}] Question: {question}")
            
            start_time = time.time()
            
            # 1. Architect Design
            architect = create_architect()
            config = architect.design_system(question)
            
            # 2. Build and Run
            builder = DynamicResearchSystemBuilder(config)
            state = builder.run(question)
            
            elapsed = time.time() - start_time
            
            # Extract metrics
            cost = sum(s.get("cost", 0.0) for s in state.get("stats", []))
            if config.stats:
                cost += config.stats.get("cost", 0.0)
            
            total_cost += cost
            
            report = state.get("findings", {}).get("writer", "") or \
                     state.get("findings", {}).get("summarizer", "") or \
                     state.get("findings", {}).get("researcher", "")
            
            print(f"  -> Judging report quality...")
            judgment = self.judge.evaluate(question, report, state)
            
            # Logic: If clarity_score > 2, we consider it a "completion" success
            passed_judge = judgment.get("clarity_score", 0) > 2
            
            result = {
                "id": case["id"],
                "question": question,
                "cost": round(cost, 4),
                "duration": round(elapsed, 2),
                "completion": passed_judge,
                "metrics": {
                    "clarity": judgment.get("clarity_score"),
                    "citation": judgment.get("citation_score"),
                    "reasoning": judgment.get("reasoning_score"),
                    "hallucination": judgment.get("hallucination_score")
                },
                "status": "✅ PASS" if passed_judge and cost < 1.0 else "❌ FAIL"
            }
            results.append(result)
            
            print(f"  -> {result['status']} | Clarity: {result['metrics']['clarity']}/5 | Cost: ${result['cost']}")
            
            # Save report and trace in question-specific subfolder
            slug = slugify_question(question)
            case_dir = os.path.join(self.results_dir, slug)
            os.makedirs(case_dir, exist_ok=True)
            
            # Report
            with open(os.path.join(case_dir, "report.md"), "w") as f:
                f.write(report)
            
            # Trace (Full State)
            # Remove objects that aren't JSON serializable if any
            trace_data = {
                "question": question,
                "config": config.dict() if hasattr(config, 'dict') else str(config),
                "state": {k: v for k, v in state.items() if k != 'llm'}, # Basic sanitization
                "judgment": judgment
            }
            with open(os.path.join(case_dir, "trace.json"), "w") as f:
                try:
                    json.dump(trace_data, f, indent=2, default=str)
                except Exception as e:
                    f.write(f"Error serializing trace: {str(e)}")

        # Summary
        passes = sum(1 for r in results if "PASS" in r["status"])
        pass_rate = (passes / len(results)) * 100
        
        print(f"\n{'='*60}")
        print(f"📊 SUMMARY")
        print(f"{'='*60}")
        print(f"Pass Rate: {pass_rate:.1f}% ({passes}/{len(results)})")
        print(f"Total Cost: ${total_cost:.4f}")
        print(f"{'='*60}\n")
        
        # Save summary
        summary_path = os.path.join(self.results_dir, "quick_eval_summary.json")
        summary = {
            "timestamp": datetime.now().isoformat(),
            "pass_rate": pass_rate,
            "total_cost": total_cost,
            "results": results
        }
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Summary and reports saved to {self.results_dir}")
        
        return results

if __name__ == "__main__":
    runner = QuickEval()
    runner.run()
