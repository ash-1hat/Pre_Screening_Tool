"""
FastAPI Medical Pre-Screening Tool
Main application entry point with API routes
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv

from routers import medical, followup, departments, patients, face_recognition, session, assessment, prescreening, voice, patient_router
from core.config import settings

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Medical Pre-Screening API starting up...")
    yield
    # Shutdown
    print("🛑 Medical Pre-Screening API shutting down...")

app = FastAPI(
    title="Medical Pre-Screening API",
    description="API for medical pre-screening with face recognition and interview capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Add validation error handler to debug 422 errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"❌ [VALIDATION ERROR] URL: {request.url}")
    print(f"❌ [VALIDATION ERROR] Method: {request.method}")
    print(f"❌ [VALIDATION ERROR] Headers: {dict(request.headers)}")
    try:
        body = await request.body()
        print(f"❌ [VALIDATION ERROR] Body: {body.decode()}")
    except:
        print("❌ [VALIDATION ERROR] Could not decode body")
    print(f"❌ [VALIDATION ERROR] Details: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc)}
    )

# Include API routers
app.include_router(patients.router, prefix="/api", tags=["patients"])
app.include_router(patient_router.router, tags=["patient-router"])
app.include_router(medical.router, prefix="/api", tags=["medical"])
app.include_router(assessment.router, prefix="/api", tags=["assessment"])
app.include_router(departments.router, prefix="/api", tags=["departments"])
app.include_router(face_recognition.router, prefix="/api", tags=["face-recognition"])
app.include_router(followup.router, prefix="/api", tags=["followup"])
app.include_router(session.router, prefix="/api", tags=["session"])
app.include_router(voice.router, prefix="/api", tags=["voice"])
app.include_router(prescreening.router, tags=["prescreening"])

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    return FileResponse("static/patient-entry.html")

@app.get("/interview")
async def serve_interview_page():
    """Serve the medical interview page"""
    return FileResponse("static/interview.html")

# Legacy face recognition page removed - functionality integrated into patient-entry.html

@app.get("/patient-entry")
async def serve_patient_entry_page():
    """Serve the new patient entry page"""
    return FileResponse("static/patient-entry.html")

@app.get("/patient-details")
async def serve_patient_details_page():
    """Serve the patient details page"""
    return FileResponse("static/patient-details.html")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Medical Pre-Screening API is running"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8001)),
        reload=True,
        reload_dirs=["./"]
    )
