from utils.llm_client import LLMClient
from agents.planner import Planner
from agents.coordinator import AgentCoordinator
from agents.checker import Checker
from agents.executor import Executor
from utils.ifc_parser import IFCParser

#llm = LLMClient()
#response = llm.generate_response("Hello, how are you?")
#print(response)  

regulation_text = open("test_regulation/1.txt", "r", encoding="utf-8").read()

ifcfile_path = "test_ifc/AC20.ifc"
ifc_parser = IFCParser()
ifc_file = ifc_parser.load_file(ifcfile_path)

# doors = ifc_parser.get_elements_by_type("IfcDoor")
# print(doors)

# property_doors = ifc_parser.extract_properties(doors[1])
# print(property_doors)
#___________________________________________________________________________

planner = Planner()
# analysis = planner._analyze_regulation(regulation_text)
# #print(analysis) 

# steps = planner._generate_plan_steps(analysis, regulation_text)
# print(steps)  

plan = planner.generate_initial_plan(regulation_text)
#print(plan)

# step1 = plan['steps'][0]
# step1_id = step1.get('step_id')
# print(step1)
#___________________________________________________________________________

coordinator = AgentCoordinator()
# plan = coordinator._request_initial_plan(regulation_text)
# print(plan) 

executor = Executor()
# result = executor.execute_single_step(step1, ifcfile_path, step1_id)
# print(result)

coordinator_response = coordinator.execute_plan(plan, ifcfile_path)
print(coordinator_response)

checker = Checker()
# validation_results = checker.evaluate_compliance(coordinator_response, regulation_text, plan)
# print(validation_results)
# all_steps_results = coordinator_response['execution_results']
# print(all_steps_results)

# summary = checker._summarize_results(coordinator_response['execution_results'])
# print(summary)

#___________________________________________________________________________
tool_requirement = ToolRequirement(
    description="Extracts the thickness of a wall from an IFC model given its ID.",
    function_name="get_wall_thickness",
    parameters=[
        {"name": "ifc_file_path", "type": "str", "description": "Path to the IFC file."},
        {"name": "wall_id", "type": "str", "description": "The unique identifier of the wall in the IFC model."}
    ],
    return_type="float",
    examples=[
        "get_wall_thickness('example.ifc', 'Wall_123') -> 0.25",
        "get_wall_thickness('building.ifc', 'Wall_456') -> 0.30"
    ]
)

tool_creator = CodeGeneratorAgent()
# tool_creator.create_tool(tool_requirement)

relevant_docs = tool_creator.rag_retriever.retrieve_relevant_docs(
                tool_requirement.description, k=5
            )
# print("Relevant Documents:")
# print(relevant_docs)

context = tool_creator._build_context(tool_requirement, relevant_docs)
# print("Context:")
# print(context)

code = tool_creator._generate_initial_code(context, tool_requirement)
# print("Generated Code:")
# print(code)

static_checker = StaticChecker()
# static_result = static_checker.check_code(code)
# print("Static Check Result:")
# print(static_result)



