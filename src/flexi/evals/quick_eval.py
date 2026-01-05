import json
import time
import os
from datetime import datetime
from flexi.agents.architect import create_architect
from flexi.agents.graph_builder import DynamicResearchSystemBuilder
from flexi.evals.metrics import calculate_task_completion
from flexi.evals.judges import QuickJudge

class QuickEval:
    def __init__(self):
        self.questions_path = os.path.join(os.path.dirname(__file__), "test_questions/tier1_questions.json")
        with open(self.questions_path, "r") as f:
            self.test_cases = json.load(f)
        self.judge = QuickJudge()
    
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
            
            passed_judge = self.judge.check_completion(question, report)
            
            # Check tool usage (simple string check in sequence for now)
            seq = state.get("execution_sequence", [])
            
            result = {
                "id": case["id"],
                "question": question,
                "cost": round(cost, 4),
                "duration": round(elapsed, 2),
                "completion": passed_judge,
                "status": "✅ PASS" if passed_judge and cost < 0.50 else "❌ FAIL"
            }
            results.append(result)
            
            print(f"  -> {result['status']} | Cost: ${result['cost']} | Time: {result['duration']}s")

        # Summary
        passes = sum(1 for r in results if "PASS" in r["status"])
        pass_rate = (passes / len(results)) * 100
        
        print(f"\n{'='*60}")
        print(f"📊 SUMMARY")
        print(f"{'='*60}")
        print(f"Pass Rate: {pass_rate:.1f}% ({passes}/{len(results)})")
        print(f"Total Cost: ${total_cost:.4f}")
        print(f"{'='*60}\n")
        
        return results

if __name__ == "__main__":
    runner = QuickEval()
    runner.run()
