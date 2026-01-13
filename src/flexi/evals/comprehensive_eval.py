import os
from datetime import datetime
from flexi.evals.runner import EvaluationRunner
from flexi.config.settings import settings

def run_comprehensive_eval():
    questions_path = os.path.join(os.path.dirname(__file__), "test_questions/tier2_questions.json")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    regime = "open" if settings.USE_OPENSOURCE_MODELS else "closed"
    subfolder = f"comprehensive/{timestamp}_{regime}"
    
    runner = EvaluationRunner(questions_path, subfolder)
    runner.run()

if __name__ == "__main__":
    run_comprehensive_eval()
