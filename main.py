import os
import shutil
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Import configuration and agents
from config import Config
from agents.coordinator import AgentCoordinator

# Import Pydantic models
from models.api_models import (
    ComplianceCheckRequest, 
    ComplianceCheckResponse, 
    HealthCheckResponse,
    ErrorResponse
)

# Global variables to store system components
coordinator = None

# Initialize system components
def initialize_system():
    """Initialize system components"""
    try:
        # Validate configuration
        Config.validate()
        
        # Initialize agent coordinator (with Planner, Executor and Checker)
        coordinator = AgentCoordinator()
        
        return coordinator
        
    except Exception as e:
        print(f"System initialization failed: {e}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan event handler"""
    global coordinator
    
    # Startup
    try:
        print("Initializing building code compliance check system ...")
        coordinator = initialize_system()
        print("System initialization completed!")
    except Exception as e:
        print(f"System initialization failed: {e}")
        # Create default components to avoid startup failure
        coordinator = AgentCoordinator()
    
    yield
    
    # Shutdown
    print("Shutting down building code compliance check system...")

# Create FastAPI application with lifespan
app = FastAPI(
    title="Building Code Compliance Check System",
    description="Multi-agent IFC file building code compliance check system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root path, returns web interface"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/check", response_model=ComplianceCheckResponse)
async def check_compliance(
    regulation: str = Form(..., description="Building code text"),
    ifc_file: UploadFile = File(..., description="IFC file")
):
    """Endpoint to check compliance of IFC file against building code"""
    try:
        # Validate request data using Pydantic
        try:
            request_data = ComplianceCheckRequest(regulation=regulation)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid regulation text: {str(e)}")
        
        # Validate file type
        if not ifc_file.filename.lower().endswith('.ifc'):
            raise HTTPException(status_code=400, detail="Only IFC file format is supported")
        
        # Save uploaded file
        file_path = os.path.join(Config.UPLOAD_DIR, ifc_file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(ifc_file.file, buffer)
        
        print(f"File saved: {file_path}")
        print(f"Code text: {request_data.regulation[:100]}...")
        
        # Execute complete compliance check with three-phase coordination
        print("Starting complete compliance check with three-phase coordination...")
        coordination_result = coordinator.execute_compliance_check(request_data.regulation, file_path)
        print("Complete compliance check coordination finished")
        
        # Clean up temporary file
        try:
            os.remove(file_path)
        except:
            pass
        
        # Return only the final report as requested
        print(f"DEBUG: coordinator returned keys: {list(coordination_result.keys())}")  # Debug 1
        final_report = coordination_result.get("final_report", {})
        print(f"DEBUG: final_report keys: {list(final_report.keys()) if final_report else 'Empty'}")  # Debug 2
        print(f"DEBUG: Returning structured response with report")  # Debug 3
        return ComplianceCheckResponse(report=final_report)
        
    except Exception as e:
        print(f"Error during check process: {e}")
        raise HTTPException(status_code=500, detail=f"Check failed: {str(e)}")

@app.post("/preview-ifc")
async def preview_ifc(ifc_file: UploadFile = File(..., description="IFC file for preview")):
    """Extract basic geometry information from IFC file for 3D preview - fixed"""
    try:
        # Validate file type
        if not ifc_file.filename.lower().endswith('.ifc'):
            raise HTTPException(status_code=400, detail="Only IFC file format is supported")
        
        # Save file temporarily 
        file_path = os.path.join(Config.UPLOAD_DIR, f"preview_{ifc_file.filename}")
        with open(file_path, "wb") as buffer:
            content = await ifc_file.read()
            buffer.write(content)
        
        # Parse IFC file using our existing parser
        from utils.ifc_parser import IFCParser
        parser = IFCParser()
        parser.load_file(file_path)
        
        # Extract building elements by type
        element_types = ['IfcWall', 'IfcDoor', 'IfcWindow', 'IfcSlab', 'IfcBeam', 'IfcColumn', 'IfcRoof', 'IfcStair']
        all_elements = []
        
        for element_type in element_types:
            elements = parser.get_elements_by_type(element_type)
            all_elements.extend(elements)
        
        # Convert to simple geometry data for frontend
        geometry_data = {
            "elements": [],
            "bounds": {"min": {"x": 0, "y": 0, "z": 0}, "max": {"x": 10, "y": 10, "z": 10}}
        }
        
        for i, element in enumerate(all_elements):
            # Extract basic properties
            element_type = element.is_a()
            element_name = getattr(element, 'Name', f'Unnamed {element_type}')
            element_id = getattr(element, 'GlobalId', f'ID_{i}')
            
            # Create simplified geometry (since we don't have real geometry extraction)
            # Use index-based positioning for demonstration
            x_pos = (i % 5) * 5
            y_pos = 0
            z_pos = (i // 5) * 3
            
            elem_data = {
                "type": element_type,
                "id": element_id,
                "name": element_name,
                "geometry": {
                    "type": "box",
                    "dimensions": get_element_dimensions(element_type),
                    "position": [x_pos, y_pos, z_pos],
                    "color": get_element_color(element_type)
                }
            }
            geometry_data["elements"].append(elem_data)
        
        # Calculate bounds
        if geometry_data["elements"]:
            positions = [elem["geometry"]["position"] for elem in geometry_data["elements"]]
            dimensions = [elem["geometry"]["dimensions"] for elem in geometry_data["elements"]]
            
            min_x = min(pos[0] - dim[0]/2 for pos, dim in zip(positions, dimensions))
            max_x = max(pos[0] + dim[0]/2 for pos, dim in zip(positions, dimensions))
            min_y = min(pos[1] - dim[1]/2 for pos, dim in zip(positions, dimensions))
            max_y = max(pos[1] + dim[1]/2 for pos, dim in zip(positions, dimensions))
            min_z = min(pos[2] - dim[2]/2 for pos, dim in zip(positions, dimensions))
            max_z = max(pos[2] + dim[2]/2 for pos, dim in zip(positions, dimensions))
            
            geometry_data["bounds"] = {
                "min": {"x": min_x, "y": min_y, "z": min_z},
                "max": {"x": max_x, "y": max_y, "z": max_z}
            }
        
        # Clean up temporary file
        try:
            os.remove(file_path)
        except:
            pass
            
        return geometry_data
        
    except Exception as e:
        print(f"Error in IFC preview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview IFC file: {str(e)}")

def get_element_color(element_type):
    """Get color for different element types"""
    colors = {
        "IFCWALL": 0xCCCCCC,
        "IFCDOOR": 0x8B4513,
        "IFCWINDOW": 0x87CEEB,
        "IFCSLAB": 0xDEB887,
        "IFCBEAM": 0x696969,
        "IFCCOLUMN": 0x696969,
        "IFCROOF": 0x8B0000,
        "IFCSTAIR": 0xA0A0A0,
        "IFCRAILING": 0x000000
    }
    return colors.get(element_type, 0x808080)

def get_element_dimensions(element_type):
    """Get default dimensions for different element types"""
    dimensions = {
        "IFCWALL": [4, 3, 0.2],      # width, height, thickness
        "IFCDOOR": [2, 2.5, 0.1],    # width, height, thickness
        "IFCWINDOW": [1.5, 1.5, 0.1], # width, height, thickness
        "IFCSLAB": [5, 0.3, 5],      # width, thickness, depth
        "IFCBEAM": [0.3, 0.5, 4],    # width, height, length
        "IFCCOLUMN": [0.3, 3, 0.3],  # width, height, depth
        "IFCROOF": [6, 0.3, 6],      # width, thickness, depth
        "IFCSTAIR": [3, 0.2, 1],     # width, step height, depth
        "IFCRAILING": [2, 1, 0.1]    # width, height, thickness
    }
    return dimensions.get(element_type, [1, 1, 1])

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check interface"""
    return HealthCheckResponse(
        status="healthy",
        system="Building Code Compliance Check System",
        version="2.0.0",
        components={
            "coordinator": "ready",
            "planner": "ready",
            "executor": "ready", 
            "checker": "ready"
        }
    )

if __name__ == "__main__":
    # Start server
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info"
    ) 