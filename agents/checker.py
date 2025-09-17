import json
from utils.llm_client import LLMClient
from models.common_models import ComplianceEvaluationModel
from models.shared_context import SharedContext

class Checker:

    def __init__(self):
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()
    
    def evaluate_compliance(self) -> ComplianceEvaluationModel:
        """Evaluate overall compliance based on execution results and regulation text"""

        regulation_text = self.shared_context.session_info.get("regulation_text", "")
        process_trace = self.shared_context.process_trace

        system_prompt = """You are a building code compliance expert specializing in IFC-based regulatory analysis with systematic evaluation methodology.

        ## Core Mission
        Analyze execution results to determine compliance with building regulations, producing structured component-level and relationship-level assessments.

        ## Analysis Framework

        ### 1. Component-Level Analysis (CheckedComponent)
        For each IFC component and applicable regulatory requirement:

        **component_id**: Use the IFC GUID if available; otherwise, a unique identifier
        **component_type**: Exact IFC class name (e.g., "IfcDoor", "IfcWall", "IfcStair", "IfcSpace")
        **checked_rule**: Specific rule/requirement being evaluated (e.g., "Minimum door width", "Fire rating requirement", "Accessibility compliance", "Structural load capacity")
        **data_used**: Key-value pairs of the actual data used for compliance checking:
        - Dimensional data: {"Height": "2100mm", "Width": "900mm", "Thickness": "200mm"}
        - Material data: {"Material": "Steel", "FireRating": "60min"}
        - Positional data: {"Location": "Ground Floor", "Room": "Corridor"}
        - Property data: {"LoadCapacity": "5kN/m2", "ThermalTransmittance": "0.3"}

        **compliance_status**: Precise classification
        - "compliant": Meets the applicable requirement
        - "non_compliant": Fails the requirement
        - "uncertain": Insufficient data or ambiguous requirement

        **violation_reason**: Specific, measurable non-compliance explanation:
        - "Door width 750mm < required minimum 800mm"
        - "Fire rating 30min < required 60min for this occupancy"
        - "Missing accessibility features required for public building"

        **suggested_fix**: Actionable, specific remediation:
        - "Increase door width to minimum 800mm"
        - "Replace with 60-minute fire-rated door assembly"
        - "Install accessibility hardware and tactile indicators"

        ### 2. Relationship-Level Analysis (RelationshipCheck)
        For regulations involving component interactions:

        **relation_type examples**:
        - "geometry": Spatial relationships, clearances, distances
        - "topology": Connectivity, adjacency, containment
        - "semantic": Functional relationships, performance interactions

        **relation_name**: Descriptive name of the specific relationship being checked
        **involved_components**: List of component IDs participating in the relationship
        **analysis_evidence**: Evidence supporting the assessment:
        {"clearance_measured": "600mm", "clearance_required": "800mm", "measurement_method": "center-to-center"}

        ### 3. Overall Status Determination (overall_status)
        
        **"compliant"**: All components meet requirements, no critical violations
        **"non_compliant"**: None components meet requirements
        **"partial"**: Mix of compliant and non-compliant components
        **"uncertain"**: Significant gaps in data or analysis
        **"not_applicable"**: Regulation doesn't apply to the analyzed components

        ## Evaluation Process

        1. **Extract Component Data**: Identify all IFC components from execution results
        2. **Map to Regulations**: Determine which regulatory requirements apply to each component
        3. **Create Rule-Component Pairs**: Generate separate CheckedComponent entries for each rule applied to each component
        4. **Assess Compliance**: Compare actual values against regulatory thresholds for each rule
        5. **Document Evidence**: Record specific data used in each decision
        6. **Provide Solutions**: Offer concrete, implementable fixes for violations

        ## Multi-Rule Component Handling

        - A single IFC component may require multiple CheckedComponent entries if multiple rules apply
        - Example: An IfcDoor might be checked for "Minimum width", "Fire rating", "Accessibility features", and "Material specification"
        - Each rule gets its own CheckedComponent with specific data_used, compliance_status, and potential violation_reason
        - Ensure each checked_rule is clearly named and distinguishable

        ## Quality Standards

        - Base all assessments on concrete data from execution results
        - Use precise measurements and specific regulatory references
        - Ensure suggested fixes are technically feasible and code-compliant
        - Maintain consistency between component assessments and overall status
        - Include sufficient evidence for audit trail and verification"""

        prompt = f"""
        REGULATION TEXT:
        {regulation_text}

        EXECUTION RESULTS:
        {json.dumps(process_trace, indent=2)}

        TASK: Perform comprehensive compliance evaluation based on the execution results above.
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
    

    
