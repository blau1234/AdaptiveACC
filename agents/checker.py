import json
from typing import Dict, List, Any
from datetime import datetime
from utils.llm_client import LLMClient
from data_models.shared_models import ComplianceEvaluationModel
from shared_context import SharedContext

class Checker:   
    
    def __init__(self, shared_context: SharedContext = None):
        self.llm_client = LLMClient()
        self.shared_context = shared_context
    
    def evaluate_compliance(self, 
                          execution_results: List[Dict[str, Any]], 
                          regulation_text: str,
                          plan: Dict[str, Any] = None) -> ComplianceEvaluationModel:
        
        system_prompt = """You are a building code compliance expert.
        Evaluate if the execution results meet the regulation requirements.
        
        Analyze the results and provide:
        - Overall compliance status (true/false)
        - Summary of compliance status
        - List of violations with severity levels (critical/major/minor)
        - List of requirements that passed
        - Actionable recommendations for compliance
        """
        
        prompt = f"""
        Building Regulation: {regulation_text}
        Execution Results: {json.dumps(execution_results, indent=2)}   
        {f"Original Plan: {json.dumps(plan, indent=2)}" if plan else "No plan information available"}
        
        Please evaluate compliance based on these results.
        """
        
        try:
            return self.llm_client.generate_response(
                prompt, 
                system_prompt,
                response_model=ComplianceEvaluationModel
            )
            
        except Exception as e:
            print(f"Compliance evaluation failed: {e}")
            raise RuntimeError(f"Compliance evaluation failed: {e}") from e
    
    def generate_report(self, 
                       evaluation: ComplianceEvaluationModel,
                       execution_results: List[Dict[str, Any]],
                       regulation_text: str) -> Dict[str, Any]:
        
        report = {
            "report_id": self._generate_report_id(),
            "generated_at": datetime.now().isoformat(),
            
            # Executive summary - information that decision makers care about most
            "executive_summary": {
                "status": "COMPLIANT" if evaluation.compliant else "NON-COMPLIANT",
                "summary": evaluation.summary,
                "critical_issues": len([v for v in evaluation.violations 
                                      if v.severity == 'critical'])
            },
            
            # Compliance details
            "compliance_details": {
                "regulation_reference": regulation_text[:200] + "...",  # Summary
                "total_requirements_checked": len(execution_results),
                "passed_requirements": evaluation.passed_checks,
                "violations": [v.model_dump() for v in evaluation.violations]
            },
            
            # Recommended actions
            "recommendations": {
                "immediate_actions": [rec for rec in evaluation.recommendations
                                    if self._is_immediate_action(rec)],
                "long_term_improvements": [rec for rec in evaluation.recommendations
                                         if not self._is_immediate_action(rec)]
            },
            
            # Detailed check results (for technical reference)
            "detailed_results": self._format_detailed_results(execution_results),
            
            # Report metadata
            "metadata": {
                "checker_version": "2.0",
                "evaluation_method": "LLM-based analysis",
                "data_sources": ["execution_results", "regulation_text", "plan"]
            }
        }
        
        return report
    
    
    
    
    def _is_immediate_action(self, recommendation: str) -> bool:
        """
        Determine if recommendation needs immediate action
        Simple classification based on keywords
        """
        immediate_keywords = ['immediate', 'urgent', 'critical', 'must', 'required', 'safety']
        return any(keyword in recommendation.lower() for keyword in immediate_keywords)
    
    def _format_detailed_results(self, execution_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format detailed results, keep all technical information
        """
        return [
            {
                "step_number": i + 1,
                "description": result.get('detail', 'No description'),
                "status": result.get('result', 'unknown'),
                "technical_details": {
                    k: v for k, v in result.items() 
                    if k not in ['detail', 'result']  # Avoid duplication
                }
            }
            for i, result in enumerate(execution_results)
        ]
    
    def _generate_report_id(self) -> str:
        """Generate unique report ID"""
        return f"RPT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # === Convenience methods ===
    
    def check_and_report(self, plan: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check compliance and generate report using shared context"""
        
        if not self.shared_context:
            raise RuntimeError("Shared context not available for compliance checking")
        
        # Get regulation text from shared context
        regulation_text = self.shared_context.session_info.get("regulation_text", "")
        if not regulation_text:
            raise RuntimeError("Regulation text not found in shared context")
        
        # Get execution results from shared context
        execution_results = []
        for result in self.shared_context.execution_summary:
            if result.get("agent") == "executor" and result.get("tool_results"):
                execution_results.extend(result["tool_results"])
            elif result.get("step_result"):
                execution_results.append(result["step_result"])
        
        evaluation = self.evaluate_compliance(execution_results, regulation_text, plan)
        report = self.generate_report(evaluation, execution_results, regulation_text)
        
        
        # Compliance check completed
        print(f"Compliance check completed - Violations: {len(evaluation.violations)}, Passed: {len(evaluation.passed_checks)}")
        
        
        return report
    
    def get_compliance_context(self) -> Dict[str, Any]:
        """Get compliance context from shared context"""
        if self.shared_context:
            return self.shared_context.get_context_for_agent("checker")
        return {}
    
    def export_report(self, report: Dict[str, Any], format: str = "json") -> str:
        """
        Export report to specified format
        Currently only supports JSON, but architecture allows easy extension
        """
        if format.lower() == "json":
            return json.dumps(report, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}. Currently only 'json' is supported.")