import json
import time
import os
from datetime import datetime
from flexi.agents.architect import create_architect
from flexi.agents.graph_builder import DynamicResearchSystemBuilder
from flexi.evals.metrics import calculate_all_metrics, calculate_tool_efficiency
from flexi.evals.judges import ReportJudge

class ComprehensiveEval:
    def __init__(self):
        self.questions_path = os.path.join(os.path.dirname(__file__), "test_questions/tier2_questions.json")
        with open(self.questions_path, "r") as f:
            self.test_cases = json.load(f)
        self.judge = ReportJudge() # Uses heavier model (e.g. Sonnet)
        # Move results out of src/ for project hygiene
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        self.results_dir = os.path.join(project_root, "eval_results", "comprehensive")
        os.makedirs(self.results_dir, exist_ok=True)
    
    def run(self):
        print(f"\n{'#'*60}")
        print(f"🔬 STARTING COMPREHENSIVE EVAL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*60}")
        
        results = []
        
        for case in self.test_cases:
            question = case["question"]
            print(f"\n[DEEP CASE {case['id']}] {question}")
            
            start_time = time.time()
            
            # 1. Design & Build
            architect = create_architect()
            config = architect.design_system(question)
            builder = DynamicResearchSystemBuilder(config)
            
            # 2. Execute
            state = builder.run(question)
            elapsed = time.time() - start_time
            
            report = state.get("findings", {}).get("writer", "No Report Generated")
            
            # 3. Judge
            print(f"  -> Judging report quality...")
            judgment = self.judge.evaluate(question, report, state)
            
            # 4. Metrics
            cost = sum(s.get("cost", 0.0) for s in state.get("stats", []))
            if config.stats:
                cost += config.stats.get("cost", 0.0)
                
            efficiency = calculate_tool_efficiency(state.get("stats", []))
            
            result = {
                "id": case["id"],
                "metrics": {
                    "clarity": judgment.get("clarity_score"),
                    "citation": judgment.get("citation_score"),
                    "reasoning": judgment.get("reasoning_score"),
                    "hallucination": judgment.get("hallucination_score"),
                    "tool_efficiency": efficiency,
                    "cost": round(cost, 4),
                    "duration": round(elapsed, 2)
                },
                "summary": judgment.get("justification")
            }
            results.append(result)
            
            print(f"  -> Clarity: {result['metrics']['clarity']}/5 | Citation: {result['metrics']['citation']}/5")
            print(f"  -> Cost: ${result['metrics']['cost']} | Efficiency: {result['metrics']['tool_efficiency']}/5")
            
            # Save report for this case
            report_path = os.path.join(self.results_dir, f"comprehensive_{case['id']}_report.md")
            with open(report_path, "w") as f:
                f.write(report)

        # Aggregation
        avg_clarity = sum(r["metrics"]["clarity"] for r in results) / len(results)
        avg_citation = sum(r["metrics"]["citation"] for r in results) / len(results)
        total_cost = sum(r["metrics"]["cost"] for r in results)
        
        print(f"\n{'#'*60}")
        print(f"📈 COMPREHENSIVE RESULTS")
        print(f"{'#'*60}")
        print(f"Avg Clarity: {avg_clarity:.1f}/5")
        print(f"Avg Citation: {avg_citation:.1f}/5")
        print(f"Total Cost: ${total_cost:.4f}")
        print(f"{'#'*60}\n")
        
        # Save summary
        summary_path = os.path.join(self.results_dir, "comprehensive_eval_summary.json")
        summary = {
            "timestamp": datetime.now().isoformat(),
            "avg_clarity": avg_clarity,
            "avg_citation": avg_citation,
            "total_cost": total_cost,
            "results": results
        }
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Summary and reports saved to {self.results_dir}")
        
        return results

if __name__ == "__main__":
    runner = ComprehensiveEval()
    runner.run()
