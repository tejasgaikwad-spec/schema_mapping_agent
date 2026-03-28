"""
Schema Mapping Agent - FastAPI Backend

API endpoints for:
- Uploading files and detecting schema
- Generating schema mappings via LLM
- Reviewing and approving mappings
- Managing stored schema maps per client
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.llm_mapper import LLMSchemaMapper, SchemaMappingResult
from app.file_reader import read_excel_for_mapping
from app.storage_manager import StorageManager
from schemas.internal_schemas import get_all_internal_fields, get_schema_for_file_type


# =============================================================================
# Pydantic Models for API
# =============================================================================

class UploadResponse(BaseModel):
    """Response from file upload endpoint"""
    success: bool
    message: str
    client_id: Optional[str] = None
    file_type: Optional[str] = None
    detected_type: Optional[str] = None
    columns: Optional[List[str]] = None
    sample_data: Optional[List[Dict[str, Any]]] = None
    sheet_names: Optional[List[str]] = None
    sheet_name: Optional[str] = None


class MappingRequest(BaseModel):
    """Request to generate schema mapping"""
    client_id: str
    columns: List[str]
    sample_data: List[Dict[str, Any]]
    file_type: str  # 'ledger' or 'tds'
    sheet_name: Optional[str] = None
    use_past_mappings: bool = True


class MappingResponse(BaseModel):
    """Response with generated schema mapping"""
    success: bool
    client_id: str
    file_type: str
    sheet_name: Optional[str]
    mappings: Dict[str, Any]
    unmapped_columns: List[str]
    required_fields_covered: List[str]
    required_fields_missing: List[str]
    overall_confidence: float
    auto_approve: bool
    message: str


class ApproveMappingRequest(BaseModel):
    """Request to approve and save a schema mapping"""
    client_id: str
    file_type: str
    sheet_name: Optional[str] = None
    mappings: Dict[str, str]  # source_column -> internal_field
    confidence_scores: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None


class ApproveMappingResponse(BaseModel):
    """Response after saving approved mapping"""
    success: bool
    message: str
    saved_path: Optional[str] = None
    version: Optional[int] = None


class SchemaMapInfo(BaseModel):
    """Info about a stored schema map"""
    filename: str
    file_type: str
    sheet_name: Optional[str]
    version: int
    updated_at: str
    column_count: int


class ClientSchemaMapsResponse(BaseModel):
    """Response with all schema maps for a client"""
    client_id: str
    schema_maps: List[SchemaMapInfo]


class InternalSchemaResponse(BaseModel):
    """Response with internal schema definition"""
    file_type: str
    fields: List[Dict[str, Any]]


# =============================================================================
# FastAPI App Initialization
# =============================================================================

app = FastAPI(
    title="Schema Mapping Agent API",
    description="LLM-powered schema mapping for TDS reconciliation pipeline",
    version="1.0.0"
)

# Serve static UI
_static_path = Path(__file__).parent.parent / "static"
if _static_path.exists():
    app.mount("/static", StaticFiles(directory=str(_static_path)), name="static")

# Initialize components
storage_manager = StorageManager(base_storage_path=os.getenv("STORAGE_PATH", "./storage"))

# Initialize LLM mapper (will fail if GROQ_API_KEY not set)
llm_mapper: Optional[LLMSchemaMapper] = None

try:
    llm_mapper = LLMSchemaMapper()
    print("✓ LLM Schema Mapper initialized successfully")
except ValueError as e:
    print(f"⚠ LLM Schema Mapper not initialized: {e}")


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Serve the interactive UI."""
    ui_path = Path(__file__).parent.parent / "static" / "index.html"
    if ui_path.exists():
        return FileResponse(str(ui_path))
    return {
        "status": "ok",
        "service": "Schema Mapping Agent API",
        "llm_ready": llm_mapper is not None
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "llm_mapper": "ready" if llm_mapper else "not_configured",
        "storage_path": str(storage_manager.base_path),
        "timestamp": datetime.utcnow().isoformat()
    }


# -----------------------------------------------------------------------------
# File Upload & Detection Endpoints
# -----------------------------------------------------------------------------

@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    client_id: Optional[str] = Form(None),
    sheet_name: Optional[str] = Form(None),
    file_type: Optional[str] = Form(None)  # 'ledger' or 'tds'
):
    """
    Upload an Excel file and detect its schema.
    
    - **file**: Excel file (.xlsx)
    - **client_id**: Optional client identifier (generated if not provided)
    - **sheet_name**: Optional specific sheet to read
    - **file_type**: Optional hint ('ledger' or 'tds')
    
    Returns detected columns, sample data, and suggested file type.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are supported")
    
    # Generate client_id if not provided
    if not client_id:
        client_id = f"temp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Read file bytes
        contents = await file.read()
        
        # Extract schema info
        result = read_excel_for_mapping(
            file_bytes=contents,
            sheet_name=sheet_name
        )
        
        # Use provided file_type or auto-detect
        detected_type = file_type or result['detected_type']
        
        return UploadResponse(
            success=True,
            message="File uploaded and analyzed successfully",
            client_id=client_id,
            file_type=detected_type,
            detected_type=result['detected_type'],
            columns=result['columns'],
            sample_data=result['sample_data'],
            sheet_names=result['sheet_names'],
            sheet_name=sheet_name or result['sheet_names'][0] if result['sheet_names'] else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


# -----------------------------------------------------------------------------
# Schema Mapping Endpoints
# -----------------------------------------------------------------------------

@app.post("/map", response_model=MappingResponse)
async def generate_mapping(request: MappingRequest):
    """
    Generate schema mapping using LLM.
    
    Takes file columns and sample data, returns suggested mappings with confidence scores.
    """
    if not llm_mapper:
        raise HTTPException(
            status_code=503,
            detail="LLM Mapper not configured. Set ANTHROPIC_API_KEY environment variable."
        )
    
    try:
        # Get past mappings if requested
        past_mappings = None
        if request.use_past_mappings:
            past_mappings = storage_manager.get_past_mappings_for_llm(
                request.client_id, 
                request.file_type
            )
        
        # Generate mapping
        result = llm_mapper.map_columns(
            source_columns=request.columns,
            sample_data=request.sample_data,
            file_type=request.file_type,
            past_mappings=past_mappings
        )
        
        # Convert mappings to dict for response
        mappings_dict = {
            source: {
                "source_column": m.source_column,
                "mapped_to": m.mapped_to,
                "confidence": m.confidence,
                "reasoning": m.reasoning
            }
            for source, m in result.mappings.items()
        }
        
        message = (
            "Mapping generated successfully. Auto-approved." 
            if result.auto_approve 
            else "Mapping generated. Human review recommended (confidence below threshold)."
        )
        
        return MappingResponse(
            success=True,
            client_id=request.client_id,
            file_type=request.file_type,
            sheet_name=request.sheet_name,
            mappings=mappings_dict,
            unmapped_columns=result.unmapped_columns,
            required_fields_covered=result.required_fields_covered,
            required_fields_missing=result.required_fields_missing,
            overall_confidence=result.overall_confidence,
            auto_approve=result.auto_approve,
            message=message
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating mapping: {str(e)}")


@app.post("/map-and-approve", response_model=ApproveMappingResponse)
async def map_and_approve(
    file: UploadFile = File(...),
    client_id: str = Form(...),
    file_type: Optional[str] = Form(None),
    sheet_name: Optional[str] = Form(None),
    auto_approve_threshold: float = Form(0.85)
):
    """
    Upload file, generate mapping, and auto-approve if confidence is high enough.
    
    This is a convenience endpoint that combines upload + mapping + approval.
    """
    if not llm_mapper:
        raise HTTPException(
            status_code=503,
            detail="LLM Mapper not configured. Set ANTHROPIC_API_KEY environment variable."
        )
    
    try:
        # Read file
        contents = await file.read()
        
        # Extract schema info
        result = read_excel_for_mapping(
            file_bytes=contents,
            sheet_name=sheet_name
        )
        
        detected_type = file_type or result['detected_type']
        actual_sheet = sheet_name or result['sheet_names'][0] if result['sheet_names'] else None
        
        # Get past mappings
        past_mappings = storage_manager.get_past_mappings_for_llm(
            client_id, 
            detected_type
        )
        
        # Generate mapping
        mapping_result = llm_mapper.map_columns(
            source_columns=result['columns'],
            sample_data=result['sample_data'],
            file_type=detected_type,
            past_mappings=past_mappings
        )
        
        # Check if auto-approval is possible
        if mapping_result.overall_confidence >= auto_approve_threshold:
            # Extract mappings and confidence scores
            mappings = {
                m.source_column: m.mapped_to 
                for m in mapping_result.mappings.values()
                if m.mapped_to != "__unmapped__"
            }
            confidence_scores = {
                m.source_column: m.confidence 
                for m in mapping_result.mappings.values()
            }
            
            # Save the mapping
            saved_path = storage_manager.save_schema_map(
                client_id=client_id,
                file_type=detected_type,
                mappings=mappings,
                confidence_scores=confidence_scores,
                sheet_name=actual_sheet,
                metadata={
                    "auto_approved": True,
                    "confidence": mapping_result.overall_confidence,
                    "source_file": file.filename
                }
            )
            
            # Load to get version
            record = storage_manager.load_schema_map(client_id, detected_type, actual_sheet)
            
            return ApproveMappingResponse(
                success=True,
                message=f"Mapping auto-approved and saved (confidence: {mapping_result.overall_confidence:.2f})",
                saved_path=saved_path,
                version=record.version if record else 1
            )
        else:
            return ApproveMappingResponse(
                success=False,
                message=f"Mapping not auto-approved (confidence: {mapping_result.overall_confidence:.2f} below threshold {auto_approve_threshold})",
                saved_path=None
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# -----------------------------------------------------------------------------
# Approval & Storage Endpoints
# -----------------------------------------------------------------------------

@app.post("/approve", response_model=ApproveMappingResponse)
async def approve_mapping(request: ApproveMappingRequest):
    """
    Approve and save a schema mapping.
    
    This endpoint is called after human review to save the approved mapping.
    """
    try:
        saved_path = storage_manager.save_schema_map(
            client_id=request.client_id,
            file_type=request.file_type,
            mappings=request.mappings,
            confidence_scores=request.confidence_scores,
            sheet_name=request.sheet_name,
            metadata=request.metadata
        )
        
        # Load to get version
        record = storage_manager.load_schema_map(
            request.client_id, 
            request.file_type, 
            request.sheet_name
        )
        
        return ApproveMappingResponse(
            success=True,
            message="Schema mapping approved and saved successfully",
            saved_path=saved_path,
            version=record.version if record else 1
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving mapping: {str(e)}")


# -----------------------------------------------------------------------------
# Schema Map Management Endpoints
# -----------------------------------------------------------------------------

@app.get("/schema-maps/{client_id}", response_model=ClientSchemaMapsResponse)
async def list_client_schema_maps(client_id: str):
    """List all schema maps for a client."""
    schema_maps = storage_manager.list_client_schema_maps(client_id)
    return ClientSchemaMapsResponse(
        client_id=client_id,
        schema_maps=[SchemaMapInfo(**sm) for sm in schema_maps]
    )


@app.get("/schema-maps/{client_id}/{file_type}")
async def get_schema_map(
    client_id: str,
    file_type: str,
    sheet_name: Optional[str] = None
):
    """Get a specific schema mapping for a client."""
    record = storage_manager.load_schema_map(client_id, file_type, sheet_name)
    
    if not record:
        raise HTTPException(status_code=404, detail="Schema map not found")
    
    return {
        "success": True,
        "schema_map": record.dict()
    }


@app.delete("/schema-maps/{client_id}/{file_type}")
async def delete_schema_map(
    client_id: str,
    file_type: str,
    sheet_name: Optional[str] = None
):
    """Delete a schema mapping for a client."""
    deleted = storage_manager.delete_schema_map(client_id, file_type, sheet_name)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Schema map not found")
    
    return {
        "success": True,
        "message": f"Schema map deleted for {client_id}/{file_type}"
    }


@app.get("/clients")
async def list_clients():
    """List all clients with stored schema maps."""
    clients = storage_manager.list_all_clients()
    return {
        "success": True,
        "clients": clients,
        "count": len(clients)
    }


# -----------------------------------------------------------------------------
# Internal Schema Endpoints
# -----------------------------------------------------------------------------

@app.get("/internal-schema/{file_type}", response_model=InternalSchemaResponse)
async def get_internal_schema(file_type: str):
    """
    Get the internal schema definition for a file type.
    
    - **file_type**: 'ledger' or 'tds'
    """
    try:
        schema = get_schema_for_file_type(file_type)
        fields = [
            {
                "name": name,
                "description": field.description,
                "data_type": field.data_type,
                "required": field.required,
                "examples": field.examples
            }
            for name, field in schema.items()
        ]
        
        return InternalSchemaResponse(
            file_type=file_type,
            fields=fields
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Run the app
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
