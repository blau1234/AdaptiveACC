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
from admin.tool_manager import ToolManager

# Import telemetry
from telemetry import init_tracing

# Import Pydantic models
from models.api_models import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    HealthCheckResponse,
    ErrorResponse,
    ToolListResponse,
    ToolDeletionResponse,
    ToolStorageStats,
    ToolInfo
)

# Global variables to store system components
coordinator = None

# Initialize system components
def initialize_system():
    """Initialize system components"""
    try:
        # Initialize Phoenix tracing if enabled
        if Config.PHOENIX_ENABLED:
            print("Initializing Phoenix tracing...")
            tracer_provider = init_tracing()
            if tracer_provider:
                print(f"Note: Traces will be sent to {Config.PHOENIX_ENDPOINT}")
            else:
                print("Phoenix tracing initialization failed, continuing without tracing")
        else:
            print("Phoenix tracing disabled in configuration")
        
        # Validate configuration
        Config.validate()
        
        # Initialize agent coordinator
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
        
        # Return process trace as the complete compliance report
        print(f"DEBUG: coordinator returned process trace with {len(coordination_result)} records")
        return ComplianceCheckResponse(report={"process_trace": coordination_result})
        
    except Exception as e:
        print(f"Error during check process: {e}")
        raise HTTPException(status_code=500, detail=f"Check failed: {str(e)}")

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


# ===== Admin Management Endpoints =====

@app.get("/admin/tools", response_model=ToolListResponse, tags=["admin"])
async def list_tools(category: Optional[str] = None):
    """List all stored domain tools, optionally filtered by category"""
    try:
        tool_manager = ToolManager()
        tools_data = tool_manager.list_stored_tools(category)

        # Convert to ToolInfo objects
        tools = [ToolInfo(**tool_data) for tool_data in tools_data]

        return ToolListResponse(
            tools=tools,
            total_count=len(tools),
            category_filter=category
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@app.delete("/admin/tools/{tool_name}", response_model=ToolDeletionResponse, tags=["admin"])
async def delete_tool(tool_name: str):
    """Delete a specific domain tool"""
    try:
        tool_manager = ToolManager()
        result = tool_manager.delete_tool(tool_name)

        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])

        return ToolDeletionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete tool: {str(e)}")


@app.get("/admin/tools/stats", response_model=ToolStorageStats, tags=["admin"])
async def get_tool_stats():
    """Get statistics about stored domain tools"""
    try:
        tool_manager = ToolManager()
        stats = tool_manager.get_storage_stats()

        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])

        return ToolStorageStats(**stats)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tool stats: {str(e)}")

if __name__ == "__main__":
    # Start server
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info"
    ) 