import json
from typing import Dict, Any, List
from flexi.core.llm_provider import get_llm
from flexi.config.settings import settings
from langchain_core.messages import HumanMessage, SystemMessage

class ReportJudge:
    """LLM-as-Judge to evaluate research reports."""
    
    def __init__(self, model: str = None):
        # Default to a cheap judge for quick evals, or Sonnet for comprehensive
        self.model = model or settings.LLM_MODEL_SYNTHESIS
        self.llm = get_llm(self.model)
        
    def evaluate(self, question: str, report: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a report against a rubric."""
        
        system_prompt = """You are an expert Research Quality Auditor. 
        Evaluate the provided research report based on the following criteria:
        1. Clarity (1-5): Is it well-structured and easy to read?
        2. Citation Accuracy (1-5): Does it cite specific findings or knowledge bases effectively?
        3. Reasoning Coherence (1-5): Does the logic flow from evidence to conclusion?
        4. Hallucination Check (0-1): Does it make claims that seem unsupported by the provided context? (0=none, 1=significant)
        
        Respond ONLY with a JSON object:
        {
            "clarity_score": int,
            "citation_score": int,
            "reasoning_score": int,
            "hallucination_score": float,
            "justification": "Short summary of why these scores were given"
        }
        """
        
        user_prompt = f"""
        RESEARCH QUESTION: {question}
        
        REPORT:
        {report}
        
        METADATA (Agent sequence, tools used):
        {json.dumps(metadata.get('execution_sequence', []), indent=2)}
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            # Clean response for JSON parsing
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            return json.loads(content)
        except Exception as e:
            return {
                "clarity_score": 1,
                "citation_score": 1,
                "reasoning_score": 1,
                "hallucination_score": 1.0,
                "justification": f"Judge failed: {str(e)}"
            }

class QuickJudge:
    """Even simpler judge for fast pass/fail checks."""
    
    def __init__(self):
        self.llm = get_llm(settings.LLM_MODEL_SYNTHESIS)
        
    def check_completion(self, question: str, report: str) -> bool:
        prompt = f"Does the following report meaningfully answer the question: '{question}'?\n\nREPORT:\n{report}\n\nAnswer only 'YES' or 'NO'."
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return "YES" in response.content.upper()
        except:
            return False
