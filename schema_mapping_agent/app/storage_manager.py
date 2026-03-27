"""
Storage Manager for Schema Mappings

Handles saving and loading approved schema_map.json files per client.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel


class SchemaMapRecord(BaseModel):
    """Record of a saved schema mapping"""
    client_id: str
    file_type: str  # 'ledger' or 'tds'
    sheet_name: Optional[str]
    mappings: Dict[str, str]  # source_column -> internal_field
    confidence_scores: Dict[str, float]
    created_at: str
    updated_at: str
    version: int = 1


class StorageManager:
    """
    Manages storage of approved schema mappings on local filesystem.
    
    Storage structure:
    storage/
    └── {client_id}/
        ├── ledger_schema_map.json
        └── tds_schema_map.json
    """
    
    def __init__(self, base_storage_path: str = "./storage"):
        """
        Initialize storage manager.
        
        Args:
            base_storage_path: Base directory for all client storage
        """
        self.base_path = Path(base_storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_client_dir(self, client_id: str) -> Path:
        """Get or create client directory."""
        client_dir = self.base_path / self._sanitize_client_id(client_id)
        client_dir.mkdir(parents=True, exist_ok=True)
        return client_dir
    
    def _sanitize_client_id(self, client_id: str) -> str:
        """Sanitize client ID for filesystem safety."""
        # Replace problematic characters
        sanitized = "".join(c if c.isalnum() or c in "-_" else "_" for c in client_id)
        return sanitized.lower()
    
    def _get_schema_map_filename(self, file_type: str, sheet_name: Optional[str] = None) -> str:
        """Generate filename for schema map."""
        file_type = file_type.lower()
        if sheet_name:
            sheet_suffix = f"_{self._sanitize_client_id(sheet_name)}"
            return f"{file_type}{sheet_suffix}_schema_map.json"
        return f"{file_type}_schema_map.json"
    
    def save_schema_map(
        self,
        client_id: str,
        file_type: str,
        mappings: Dict[str, str],
        confidence_scores: Optional[Dict[str, float]] = None,
        sheet_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save an approved schema mapping for a client.
        
        Args:
            client_id: Unique identifier for the client (e.g., company PAN, UUID)
            file_type: 'ledger' or 'tds'
            mappings: Dictionary mapping source columns to internal fields
            confidence_scores: Optional confidence scores for each mapping
            sheet_name: Optional sheet name for multi-sheet files
            metadata: Optional additional metadata
            
        Returns:
            Path to the saved file
        """
        client_dir = self._get_client_dir(client_id)
        filename = self._get_schema_map_filename(file_type, sheet_name)
        filepath = client_dir / filename
        
        now = datetime.utcnow().isoformat()
        
        # Check if file exists to preserve version history
        version = 1
        if filepath.exists():
            try:
                existing = json.loads(filepath.read_text())
                version = existing.get('version', 1) + 1
            except:
                pass
        
        record = {
            "client_id": client_id,
            "file_type": file_type,
            "sheet_name": sheet_name,
            "mappings": mappings,
            "confidence_scores": confidence_scores or {},
            "created_at": now,
            "updated_at": now,
            "version": version,
            "metadata": metadata or {}
        }
        
        filepath.write_text(json.dumps(record, indent=2))
        
        return str(filepath)
    
    def load_schema_map(
        self,
        client_id: str,
        file_type: str,
        sheet_name: Optional[str] = None
    ) -> Optional[SchemaMapRecord]:
        """
        Load a saved schema mapping for a client.
        
        Args:
            client_id: Client identifier
            file_type: 'ledger' or 'tds'
            sheet_name: Optional sheet name
            
        Returns:
            SchemaMapRecord if found, None otherwise
        """
        client_dir = self._get_client_dir(client_id)
        filename = self._get_schema_map_filename(file_type, sheet_name)
        filepath = client_dir / filename
        
        if not filepath.exists():
            return None
        
        try:
            data = json.loads(filepath.read_text())
            return SchemaMapRecord(**data)
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error loading schema map: {e}")
            return None
    
    def get_mappings_dict(
        self,
        client_id: str,
        file_type: str,
        sheet_name: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Get just the mappings dictionary for a client.
        
        Returns:
            Dictionary of source_column -> internal_field, or None if not found
        """
        record = self.load_schema_map(client_id, file_type, sheet_name)
        if record:
            return record.mappings
        return None
    
    def list_client_schema_maps(self, client_id: str) -> List[Dict[str, Any]]:
        """
        List all schema maps for a client.
        
        Returns:
            List of schema map metadata
        """
        client_dir = self._get_client_dir(client_id)
        schema_maps = []
        
        for filepath in client_dir.glob("*_schema_map.json"):
            try:
                data = json.loads(filepath.read_text())
                schema_maps.append({
                    "filename": filepath.name,
                    "file_type": data.get("file_type"),
                    "sheet_name": data.get("sheet_name"),
                    "version": data.get("version"),
                    "updated_at": data.get("updated_at"),
                    "column_count": len(data.get("mappings", {}))
                })
            except:
                pass
        
        return schema_maps
    
    def delete_schema_map(
        self,
        client_id: str,
        file_type: str,
        sheet_name: Optional[str] = None
    ) -> bool:
        """
        Delete a schema mapping for a client.
        
        Returns:
            True if deleted, False if not found
        """
        client_dir = self._get_client_dir(client_id)
        filename = self._get_schema_map_filename(file_type, sheet_name)
        filepath = client_dir / filename
        
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    
    def list_all_clients(self) -> List[str]:
        """List all client IDs that have stored schema maps."""
        clients = []
        for item in self.base_path.iterdir():
            if item.is_dir():
                clients.append(item.name)
        return clients
    
    def get_past_mappings_for_llm(
        self,
        client_id: str,
        file_type: str
    ) -> Optional[Dict[str, str]]:
        """
        Get past mappings in a format suitable for LLM context.
        
        This returns the most recent mapping for the file type,
        regardless of sheet name, to use as hints.
        
        Returns:
            Dictionary of source_column -> internal_field
        """
        client_dir = self._get_client_dir(client_id)
        
        # Find all schema maps of this file type
        pattern = f"{file_type}*_schema_map.json"
        matches = list(client_dir.glob(pattern))
        
        if not matches:
            return None
        
        # Get the most recently updated one
        latest = max(matches, key=lambda p: p.stat().st_mtime)
        
        try:
            data = json.loads(latest.read_text())
            return data.get("mappings")
        except:
            return None
