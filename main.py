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
        coordinator = AgentCoordinator(Config.OPENAI_MODEL_NAME, Config.OPENAI_API_KEY)
        
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
        print("Initializing building code compliance check system with three-agent architecture...")
        coordinator = initialize_system()
        print("System initialization completed!")
    except Exception as e:
        print(f"System initialization failed: {e}")
        # Create default components to avoid startup failure
        coordinator = AgentCoordinator("gpt-4", "dummy_key")
    
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


@app.post("/check")
async def check_compliance(
    regulation: str = Form(..., description="Building code text"),
    ifc_file: UploadFile = File(..., description="IFC file")
):
    """
    Execute building code compliance check using three-phase coordination
    
    Args:
        regulation: Building code text
        ifc_file: Uploaded IFC file
        
    Returns:
        ComplianceCheckResponse: Complete check result with coordination info
    """
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
        
        # Return raw dict for now until agent models are fully converted
        # TODO: Convert to Pydantic models after updating agent code
        return {
            "plan": coordination_result.get("plan", {}),
            "results": coordination_result.get("execution_results", []),
            "report": coordination_result.get("final_report", {}),
            "coordination_info": {
                "execution_status": coordination_result.get("execution_status", "unknown"),
                "feedback_rounds_used": coordination_result.get("feedback_rounds_used", 0),
                "steps_completed": coordination_result.get("steps_completed", 0),
                "total_steps": coordination_result.get("total_steps", 0),
                "communication_summary": coordinator.get_communication_summary()
            }
        }
        
    except Exception as e:
        print(f"Error during check process: {e}")
        raise HTTPException(status_code=500, detail=f"Check failed: {str(e)}")

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check interface"""
    return HealthCheckResponse(
        status="healthy",
        system="Building Code Compliance Check System (Three-Phase Coordination)",
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