import os
import shutil
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Import configuration and agents
from config import Config
from agents.compliance_agent import ComplianceAgent

# Import telemetry
from telemetry import init_tracing

# Import Pydantic models
from models.api_models import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    HealthCheckResponse,
    ErrorResponse
)
from models.common_models import ComplianceEvaluationModel

# Global variables to store system components
compliance_agent = None

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

        # Initialize compliance agent
        agent = ComplianceAgent()

        return agent
        
    except Exception as e:
        print(f"System initialization failed: {e}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan event handler"""
    global compliance_agent

    # Startup
    try:
        print("Initializing building code compliance check system ...")
        compliance_agent = initialize_system()
        print("System initialization completed!")
    except Exception as e:
        print(f"System initialization failed: {e}")
        # Create default components to avoid startup failure
        compliance_agent = ComplianceAgent()

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

@app.get("/assets/{file_path:path}")
async def serve_assets(file_path: str):
    """Serve static assets"""
    print(f"[ASSETS] Request for: {file_path}")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    asset_file = os.path.join(base_dir, "templates", "assets", file_path)
    print(f"[ASSETS] Looking for file at: {asset_file}")
    print(f"[ASSETS] File exists: {os.path.exists(asset_file)}")
    if os.path.exists(asset_file):
        print(f"[ASSETS] Serving file: {asset_file}")
        return FileResponse(asset_file)
    print(f"[ASSETS] File not found!")
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/check", response_model=ComplianceEvaluationModel)
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

        # Execute complete compliance check
        print("Starting compliance check...")
        agent_result = compliance_agent.execute_compliance_check(request_data.regulation, file_path)
        print("Compliance check finished")

        # Clean up temporary file
        try:
            os.remove(file_path)
        except:
            pass

        # Extract compliance result from agent result
        if agent_result.status == "success" and agent_result.compliance_result:
            return agent_result.compliance_result  # FastAPI will serialize automatically
        else:
            error_msg = agent_result.error or "Compliance check failed"
            raise HTTPException(status_code=500, detail=error_msg)

    except Exception as e:
        print(f"Error during check process: {e}")
        raise HTTPException(status_code=500, detail=f"Check failed: {str(e)}")

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check interface"""
    return HealthCheckResponse(
        status="healthy",
        system="Building Code Compliance Check System",
        version="3.0.0",
        components={
            "compliance_agent": "ready",
            "agent_tools": "ready"
        }
    )

if __name__ == "__main__":
    # Start server
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        reload_excludes=["ifc_tools/generated/**/*.py"],  # Exclude dynamically generated tools from hot reload
        log_level="info"
    ) 
