import json
from typing import Dict, List, Any
from datetime import datetime
from utils.llm_client import LLMClient
from models.blackboard_models import BlackboardMixin

class Checker(BlackboardMixin):   
    
    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
    
    def evaluate_compliance(self, 
                          execution_results: List[Dict[str, Any]], 
                          regulation_text: str,
                          plan: Dict[str, Any] = None) -> Dict[str, Any]:
        
        system_prompt = """You are a building code compliance expert.
        Evaluate if the execution results meet the regulation requirements.
        Return a JSON object with this structure:
        {
            "compliant": true/false,
            "summary": "One-line summary of compliance status",
            "violations": [
                {
                    "requirement": "Which requirement was violated",
                    "severity": "critical|major|minor",
                    "details": "What specifically failed"
                }
            ],
            "passed_checks": [
                "List of requirements that passed"
            ],
            "recommendations": [
                "Actionable steps to achieve compliance"
            ]
        }
        """
        
        prompt = f"""
        Building Regulation: {regulation_text}
        Execution Results: {json.dumps(execution_results, indent=2)}   
        {f"Original Plan: {json.dumps(plan, indent=2)}" if plan else "No plan information available"}
        Please evaluate compliance based on these results.
        """
        
        try:
            response = self.llm_client.generate_response(prompt, system_prompt)
            evaluation = self._extract_json_from_response(response)
            
            # Ensure required fields exist with defaults
            evaluation.setdefault('compliant', False)
            # Remove confidence field
            evaluation.setdefault('summary', 'No summary generated')
            evaluation.setdefault('violations', [])
            evaluation.setdefault('passed_checks', [])
            evaluation.setdefault('recommendations', [])
            
            # Add metadata
            evaluation['timestamp'] = datetime.now().isoformat()
            evaluation['total_checks'] = len(execution_results)
            
            return evaluation
            
        except Exception as e:
            print(f"Compliance evaluation failed: {e}")
            raise RuntimeError(f"Compliance evaluation failed: {e}") from e
    
    def generate_report(self, 
                       evaluation: Dict[str, Any],
                       execution_results: List[Dict[str, Any]],
                       regulation_text: str) -> Dict[str, Any]:
        
        report = {
            "report_id": self._generate_report_id(),
            "generated_at": datetime.now().isoformat(),
            
            # Executive summary - information that decision makers care about most
            "executive_summary": {
                "status": "COMPLIANT" if evaluation['compliant'] else "NON-COMPLIANT",
                "summary": evaluation['summary'],
                "critical_issues": len([v for v in evaluation.get('violations', []) 
                                      if v.get('severity') == 'critical'])
            },
            
            # Compliance details
            "compliance_details": {
                "regulation_reference": regulation_text[:200] + "...",  # Summary
                "total_requirements_checked": evaluation['total_checks'],
                "passed_requirements": evaluation.get('passed_checks', []),
                "violations": evaluation.get('violations', [])
            },
            
            # Recommended actions
            "recommendations": {
                "immediate_actions": [rec for rec in evaluation.get('recommendations', [])
                                    if self._is_immediate_action(rec)],
                "long_term_improvements": [rec for rec in evaluation.get('recommendations', [])
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
    
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response
        Handle possible markdown code block format
        """
        import re
        
        # Try direct parsing
        try:
            return json.loads(response.strip())
        except:
            pass
        
        # Extract JSON from markdown code block
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Find JSON object
        brace_match = re.search(r'\{.*\}', response, re.DOTALL)
        if brace_match:
            return json.loads(brace_match.group())
        
        raise ValueError("Cannot extract JSON from response")
    
    
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
    
    def check_and_report(self, 
                        execution_results: List[Dict[str, Any]], 
                        regulation_text: str,
                        plan: Dict[str, Any] = None) -> Dict[str, Any]:
       
        # Log compliance check start to blackboard
        if hasattr(self, '_blackboard') and self._blackboard:
            self.log_communication("coordinator", "compliance_check_start", {
                "execution_results_count": len(execution_results),
                "regulation_length": len(regulation_text),
                "has_plan": plan is not None
            })
            
            # Use blackboard data if parameters not provided
            if not regulation_text and hasattr(self, '_blackboard'):
                regulation_text = self.get_regulation_text()
            if not plan and hasattr(self, '_blackboard'):
                plan = self.get_current_plan()
            if not execution_results and hasattr(self, '_blackboard'):
                execution_results = self.get_execution_results()
        
        evaluation = self.evaluate_compliance(execution_results, regulation_text, plan)
        report = self.generate_report(evaluation, execution_results, regulation_text)
        
        # Log completion to blackboard
        if hasattr(self, '_blackboard') and self._blackboard:
            self.log_communication("checker", "compliance_check_completed", {
                "compliant": evaluation.get("compliant", False),
                "violations_count": len(evaluation.get("violations", [])),
                "passed_checks_count": len(evaluation.get("passed_checks", []))
            })
        
        return report
    
    def export_report(self, report: Dict[str, Any], format: str = "json") -> str:
        """
        Export report to specified format
        Currently only supports JSON, but architecture allows easy extension
        """
        if format.lower() == "json":
            return json.dumps(report, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}. Currently only 'json' is supported.")