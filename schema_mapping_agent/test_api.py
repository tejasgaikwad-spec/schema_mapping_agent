"""
Test script for Schema Mapping Agent API

This script demonstrates how to use the API endpoints with your sample files.
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint."""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_internal_schema():
    """Test internal schema endpoint."""
    print("\n=== Testing Internal Schema Endpoint ===")
    
    # Test ledger schema
    response = requests.get(f"{BASE_URL}/internal-schema/ledger")
    print(f"\nLedger Schema (Status: {response.status_code}):")
    data = response.json()
    print(f"Fields: {len(data['fields'])}")
    for field in data['fields'][:5]:  # Show first 5
        print(f"  - {field['name']}: {field['description']}")
    
    # Test TDS schema
    response = requests.get(f"{BASE_URL}/internal-schema/tds")
    print(f"\nTDS Schema (Status: {response.status_code}):")
    data = response.json()
    print(f"Fields: {len(data['fields'])}")
    for field in data['fields'][:5]:  # Show first 5
        print(f"  - {field['name']}: {field['description']}")


def test_upload_tally():
    """Test upload with Tally file."""
    print("\n=== Testing Upload (Tally File) ===")
    
    file_path = Path("../upload/Tally extract.xlsx")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return None
    
    with open(file_path, "rb") as f:
        files = {"file": ("Tally extract.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {"client_id": "HPC_LTD_TEST"}
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Detected Type: {result.get('detected_type')}")
    print(f"Columns: {len(result.get('columns', []))}")
    print(f"Sample columns: {result.get('columns', [])[:5]}")
    print(f"Sheet names: {result.get('sheet_names', [])}")
    
    return result


def test_upload_form26():
    """Test upload with Form 26 file."""
    print("\n=== Testing Upload (Form 26 File) ===")
    
    file_path = Path("../upload/Form 26 - Deduction Register....xlsx")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return None
    
    with open(file_path, "rb") as f:
        files = {"file": ("Form 26.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {"client_id": "HPC_LTD_TEST"}
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Detected Type: {result.get('detected_type')}")
    print(f"Columns: {len(result.get('columns', []))}")
    print(f"Sample columns: {result.get('columns', [])[:5]}")
    
    return result


def test_generate_mapping(upload_result):
    """Test mapping generation."""
    print("\n=== Testing Generate Mapping ===")
    
    if not upload_result:
        print("No upload result to use")
        return None
    
    payload = {
        "client_id": upload_result["client_id"],
        "columns": upload_result["columns"],
        "sample_data": upload_result["sample_data"],
        "file_type": upload_result["detected_type"],
        "use_past_mappings": True
    }
    
    response = requests.post(f"{BASE_URL}/map", json=payload)
    print(f"Status: {response.status_code}")
    
    result = response.json()
    print(f"Overall Confidence: {result.get('overall_confidence')}")
    print(f"Auto Approve: {result.get('auto_approve')}")
    print(f"Required Fields Covered: {result.get('required_fields_covered', [])}")
    print(f"Required Fields Missing: {result.get('required_fields_missing', [])}")
    print(f"\nMappings:")
    for source, mapping in list(result.get('mappings', {}).items())[:5]:
        print(f"  '{source}' → '{mapping['mapped_to']}' (confidence: {mapping['confidence']})")
    
    return result


def test_approve_mapping(mapping_result, upload_result):
    """Test approving and saving a mapping."""
    print("\n=== Testing Approve Mapping ===")
    
    if not mapping_result:
        print("No mapping result to approve")
        return None
    
    # Extract simple mappings and confidence scores
    mappings = {
        m["source_column"]: m["mapped_to"]
        for m in mapping_result["mappings"].values()
        if m["mapped_to"] != "__unmapped__"
    }
    confidence_scores = {
        m["source_column"]: m["confidence"]
        for m in mapping_result["mappings"].values()
    }
    
    payload = {
        "client_id": upload_result["client_id"],
        "file_type": upload_result["detected_type"],
        "mappings": mappings,
        "confidence_scores": confidence_scores,
        "metadata": {
            "test": True,
            "source": "test_api.py"
        }
    }
    
    response = requests.post(f"{BASE_URL}/approve", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()


def test_list_schema_maps(client_id):
    """Test listing schema maps for a client."""
    print(f"\n=== Testing List Schema Maps ({client_id}) ===")
    
    response = requests.get(f"{BASE_URL}/schema-maps/{client_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_map_and_approve():
    """Test the combined map-and-approve endpoint."""
    print("\n=== Testing Map and Approve (Combined) ===")
    
    file_path = Path("../upload/Form 26 - Deduction Register....xlsx")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return None
    
    with open(file_path, "rb") as f:
        files = {"file": ("Form 26.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {
            "client_id": "HPC_LTD_AUTO",
            "auto_approve_threshold": 0.85
        }
        response = requests.post(f"{BASE_URL}/map-and-approve", files=files, data=data)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()


def run_all_tests():
    """Run all tests in sequence."""
    print("=" * 60)
    print("Schema Mapping Agent API Test Suite")
    print("=" * 60)
    
    # Test health
    if not test_health():
        print("\n⚠️ Server not running or not healthy. Please start the server first.")
        print("   Run: uvicorn app.main:app --reload")
        return
    
    # Test internal schema
    test_internal_schema()
    
    # Test upload with Tally file
    tally_upload = test_upload_tally()
    
    if tally_upload:
        # Test mapping generation
        tally_mapping = test_generate_mapping(tally_upload)
        
        if tally_mapping:
            # Test approve
            test_approve_mapping(tally_mapping, tally_upload)
    
    # Test upload with Form 26
    form26_upload = test_upload_form26()
    
    if form26_upload:
        # Test mapping generation
        form26_mapping = test_generate_mapping(form26_upload)
        
        if form26_mapping:
            # Test approve
            test_approve_mapping(form26_mapping, form26_upload)
    
    # Test map-and-approve combined
    test_map_and_approve()
    
    # Test list schema maps
    test_list_schema_maps("HPC_LTD_TEST")
    test_list_schema_maps("HPC_LTD_AUTO")
    
    print("\n" + "=" * 60)
    print("Test Suite Complete!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
