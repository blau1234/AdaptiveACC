import json
from typing import Dict, List, Any
from datetime import datetime
from utils.llm_client import LLMClient

class Checker:   
    
    def __init__(self):
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
            "confidence": 0.0-1.0,
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
        
        # Prepare simplified summary of execution results
        results_summary = self._summarize_results(execution_results)
        
        prompt = f"""
        Building Regulation: {regulation_text}
        Execution Results: {json.dumps(results_summary, indent=2)}   
        {f"Original Plan: {json.dumps(plan, indent=2)}" if plan else "No plan information available"}
        Please evaluate compliance based on these results.
        """
        
        try:
            response = self.llm_client.generate_response(prompt, system_prompt)
            evaluation = self._extract_json_from_response(response)
            
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
                "confidence": evaluation['confidence'],
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
    
    def _summarize_results(self, execution_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simplify execution results into format that LLM can easily understand
        Remove redundant information, keep key judgment elements
        """
        summary = []
        for i, result in enumerate(execution_results):
            summary.append({
                "step": i + 1,
                "checked": result.get('detail', 'Unknown check'),
                "result": result.get('result', 'unknown'),
                "issues": result.get('issues', []),
                "elements": result.get('elements_checked', [])
            })
        return summary
    
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
        """
        One-stop method: evaluate and generate report
        This is the method most users will call
        """
        evaluation = self.evaluate_compliance(execution_results, regulation_text, plan)
        report = self.generate_report(evaluation, execution_results, regulation_text)
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