from agent_tools.web_search import WebSearch
from utils.llm_client import LLMClient

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

# NEW API - use RegulationInterpretationTool and pass via SharedContext
from agent_tools.regulation_interpretation import RegulationInterpretationTool
from models.shared_context import SharedContext
from agent_tools.subgoal_management import SubgoalManagement

# shared_context = SharedContext.get_instance()
# shared_context.initialize_session("test_session", regulation_text, ifcfile_path)

# interpretation_tool = RegulationInterpretationTool()
# interpretation_result = interpretation_tool.generate_interpretation(regulation_text)
# print(interpretation_result)

# subgoal_mgmt = SubgoalManagement()
# subgoals_result = subgoal_mgmt.generate_subgoals()
# print(subgoals_result)

#_______________________________________________________________________

# Web search tool
# web_search_tool = WebSearch()
# web_search_result = web_search_tool.search_and_summarize("IFC clear width definition", "understand clear width for door compliance checking")
# print(web_search_result)

#___________________________________________________________________________
from agent_tools.ifc_tool_creation_and_fix.spec_generator import SpecGenerator
from agent_tools.ifc_tool_creation_and_fix.code_generator import CodeGenerator
from agent_tools.ifc_tool_creation_and_fix.ifc_tool_creation import ToolCreation
from agent_tools.ifc_tool_execution import ToolExecution

# spec_generator = SpecGenerator()
# spec_generation_result = spec_generator.generate_spec("Determine the unit system and measurement units used in an IFC file, particularly for length/distance measurements. ")
# # print(spec_generation_result)

# code_generator = CodeGenerator()
# code_generation_result = code_generator.generate_code(spec_generation_result, [])
# print(code_generation_result)

# tool_creation = ToolCreation()
# creation_result = tool_creation.create_ifc_tool("Determine the unit system and measurement units used in an IFC file, particularly for length/distance measurements. ")
# # print(creation_result)

# tool_execution = ToolExecution()
# tool_name = creation_result.result.ifc_tool_name
# # Construct actual parameter dictionary (not the parameter definition list)
# parameters = {"ifc_file_path": ifcfile_path}
# execution_result = tool_execution.execute_in_sandbox(tool_name, parameters)
# print(execution_result)

#___________________________________________________________________________
# from measure_stair_width import measure_stair_clear_width
# stair_result = measure_stair_clear_width(ifcfile_path, "38a9vdh9bF5Qg28GWyHhlr")
# print(stair_result)

from ifc_tools.generated.attributes import extract_stair_riser_height
riser_result = extract_stair_riser_height.extract_stair_riser_height(ifcfile_path, "38a9vdh9bF5Qg28GWyHhlr")
print(riser_result)

