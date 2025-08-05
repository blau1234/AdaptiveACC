"""
演示模块化工具库的使用

展示如何：
1. 使用默认工具库
2. 创建自定义工具
3. 混合使用默认和自定义工具
4. 按类别筛选工具
"""

import os
import sys
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def demo_default_tool_library():
    """演示默认工具库的使用"""
    
    print("Demo: Default Tool Library")
    print("=" * 40)
    
    from tools.ifc_parser import (
        create_default_tool_library, 
        get_tools_by_category,
        get_tool_names_by_category,
        print_tool_library_info
    )
    
    # 1. 展示完整工具库信息
    print("1. Complete Tool Library:")
    print_tool_library_info()
    
    # 2. 按类别获取工具
    print("2. Tools by Category:")
    categories = get_tool_names_by_category()
    for category, tool_names in categories.items():
        print(f"   {category}: {tool_names}")
    
    # 3. 获取特定类别的工具
    print("\n3. Validation Tools Only:")
    validation_tools = get_tools_by_category("validation")
    for name, tool in validation_tools.items():
        print(f"   - {name}: {tool.description}")

def demo_custom_tool_creation():
    """演示自定义工具的创建"""
    
    print("\n\nDemo: Custom Tool Creation")
    print("=" * 40)
    
    from tools.ifc_parser import Tool
    
    # 创建自定义工具
    def custom_energy_efficiency_tool(ifc_file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """自定义能效检查工具"""
        if not os.path.exists(ifc_file_path):
            return {
                "result": "fail",
                "detail": "IFC file not found",
                "elements_checked": [],
                "issues": ["File not found"]
            }
        
        # 模拟能效检查
        efficiency_rating = parameters.get("target_rating", "B")
        building_type = parameters.get("building_type", "office")
        
        import random
        current_rating = random.choice(["A", "B", "C", "D"])
        
        compliant = ord(current_rating) <= ord(efficiency_rating)
        
        return {
            "result": "pass" if compliant else "fail",
            "detail": f"Energy efficiency check for {building_type}: current rating {current_rating}, target {efficiency_rating}",
            "energy_rating": current_rating,
            "target_rating": efficiency_rating,
            "elements_checked": ["HVAC systems", "Insulation", "Windows"],
            "issues": [] if compliant else [f"Current rating {current_rating} below target {efficiency_rating}"]
        }
    
    # 创建工具实例
    energy_tool = Tool(
        name="energy_efficiency_checker",
        description="Checks building energy efficiency compliance with green building standards",
        category="sustainability",
        function=custom_energy_efficiency_tool,
        parameters_schema={
            "target_rating": {"type": "string", "required": False, "description": "Target energy rating (A-D)"},
            "building_type": {"type": "string", "required": False, "description": "Type of building"}
        }
    )
    
    print("1. Custom Tool Created:")
    print(f"   Name: {energy_tool.name}")
    print(f"   Category: {energy_tool.category}")
    print(f"   Description: {energy_tool.description}")
    
    # 测试自定义工具
    print("\n2. Testing Custom Tool:")
    with open("temp_test.ifc", "w") as f:
        f.write("# Temporary IFC file for testing")
    
    try:
        result = energy_tool.function("temp_test.ifc", {"target_rating": "A", "building_type": "office"})
        print(f"   Result: {result['result']}")
        print(f"   Detail: {result['detail']}")
        print(f"   Energy Rating: {result.get('energy_rating', 'N/A')}")
    finally:
        if os.path.exists("temp_test.ifc"):
            os.remove("temp_test.ifc")

def demo_mixed_tool_library():
    """演示混合使用默认和自定义工具"""
    
    print("\n\nDemo: Mixed Tool Library")
    print("=" * 40)
    
    from tools.ifc_parser import create_default_tool_library, Tool
    from agents.executor import Executor
    from unittest.mock import patch
    
    # 创建自定义工具
    def seismic_compliance_tool(ifc_file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """地震合规性检查工具"""
        seismic_zone = parameters.get("seismic_zone", "moderate")
        
        import random
        compliance_score = random.uniform(0.7, 1.0)
        
        return {
            "result": "pass" if compliance_score >= 0.85 else "fail",
            "detail": f"Seismic compliance check for zone {seismic_zone}: score {compliance_score:.2f}",
            "compliance_score": compliance_score,
            "seismic_zone": seismic_zone,
            "elements_checked": ["Structural supports", "Connections", "Foundation"],
            "issues": [] if compliance_score >= 0.85 else ["Insufficient seismic resistance"]
        }
    
    # 获取默认工具库
    default_tools = create_default_tool_library()
    
    # 添加自定义工具
    custom_tools = {
        "seismic_compliance": Tool(
            name="seismic_compliance",
            description="Checks building compliance with seismic safety standards",
            category="safety",
            function=seismic_compliance_tool,
            parameters_schema={
                "seismic_zone": {"type": "string", "required": False, "description": "Seismic zone classification"}
            }
        )
    }
    
    # 合并工具库
    mixed_tool_library = {**default_tools, **custom_tools}
    
    print("1. Mixed Tool Library Stats:")
    print(f"   Default tools: {len(default_tools)}")
    print(f"   Custom tools: {len(custom_tools)}")
    print(f"   Total tools: {len(mixed_tool_library)}")
    
    print("\n2. All Available Tools:")
    categories = {}
    for name, tool in mixed_tool_library.items():
        if tool.category not in categories:
            categories[tool.category] = []
        categories[tool.category].append(name)
    
    for category, tool_names in categories.items():
        print(f"   {category}: {tool_names}")
    
    # 创建使用混合工具库的执行器
    print("\n3. Testing Mixed Tool Library with Executor:")
    
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test_key',
        'OPENAI_MODEL_NAME': 'gpt-4'
    }):
        executor = Executor(tool_library=mixed_tool_library)
        
        print(f"   Executor tool count: {len(executor.tool_library)}")
        print(f"   Available categories: {set(tool.category for tool in executor.tool_library.values())}")
        
        # 演示工具建议功能
        safety_step = {
            "description": "Check seismic compliance for high-rise building",
            "task_type": "safety"
        }
        
        suggested_tools = executor._suggest_relevant_tools(
            step=safety_step,
            current_state={"observation": "Starting safety check"}
        )
        
        print(f"\n4. Suggested Tools for Safety Check:")
        for tool in suggested_tools:
            print(f"   - {tool.name} ({tool.category}): {tool.description}")

def demo_dynamic_tool_loading():
    """演示动态工具加载"""
    
    print("\n\nDemo: Dynamic Tool Loading")
    print("=" * 40)
    
    from tools.ifc_parser import Tool
    
    # 模拟从配置文件或数据库加载工具配置
    tool_configs = [
        {
            "name": "wind_load_analysis",
            "description": "Analyzes building resistance to wind loads",
            "category": "structural",
            "parameters": {
                "wind_speed": {"type": "number", "required": True, "description": "Design wind speed"},
                "building_height": {"type": "number", "required": True, "description": "Building height in meters"}
            }
        },
        {
            "name": "thermal_performance",
            "description": "Evaluates building thermal performance and insulation",
            "category": "energy",
            "parameters": {
                "climate_zone": {"type": "string", "required": False, "description": "Climate zone classification"}
            }
        }
    ]
    
    print("1. Loading Tools from Configuration:")
    
    dynamic_tools = {}
    
    for config in tool_configs:
        # 为每个配置创建一个通用的工具函数
        def create_tool_function(tool_name: str):
            def tool_function(ifc_file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
                if not os.path.exists(ifc_file_path):
                    return {
                        "result": "fail",
                        "detail": "IFC file not found",
                        "elements_checked": [],
                        "issues": ["File not found"]
                    }
                
                # 模拟工具执行
                import random
                success = random.random() > 0.3
                
                return {
                    "result": "pass" if success else "fail",
                    "detail": f"{tool_name} completed with parameters: {parameters}",
                    "elements_checked": [f"{tool_name}_analysis"],
                    "issues": [] if success else [f"{tool_name} found issues"]
                }
            
            return tool_function
        
        # 创建工具实例
        tool = Tool(
            name=config["name"],
            description=config["description"],
            category=config["category"],
            function=create_tool_function(config["name"]),
            parameters_schema=config["parameters"]
        )
        
        dynamic_tools[config["name"]] = tool
        print(f"   ✓ Loaded: {config['name']} ({config['category']})")
    
    print(f"\n2. Successfully loaded {len(dynamic_tools)} dynamic tools")
    
    # 演示动态工具的使用
    print("\n3. Testing Dynamic Tool:")
    wind_tool = dynamic_tools["wind_load_analysis"]
    
    with open("temp_test.ifc", "w") as f:
        f.write("# Temporary IFC file")
    
    try:
        result = wind_tool.function("temp_test.ifc", {"wind_speed": 50, "building_height": 100})
        print(f"   Result: {result['result']}")
        print(f"   Detail: {result['detail']}")
    finally:
        if os.path.exists("temp_test.ifc"):
            os.remove("temp_test.ifc")

if __name__ == "__main__":
    print("Modular Tool Library Demonstration")
    print("=" * 60)
    
    try:
        # 运行所有演示
        demo_default_tool_library()
        demo_custom_tool_creation()
        demo_mixed_tool_library()
        demo_dynamic_tool_loading()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKEY BENEFITS OF MODULAR TOOL LIBRARY:")
        print("✓ Easy to extend with new tools")
        print("✓ Clear separation of concerns") 
        print("✓ Reusable across different components")
        print("✓ Support for dynamic tool loading")
        print("✓ Category-based organization")
        print("✓ Flexible parameter schemas")
        
    except Exception as e:
        print(f"\nDemo failed: {e}")
        import traceback
        traceback.print_exc()