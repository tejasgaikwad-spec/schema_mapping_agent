"""
Example: Using Schema Mapping Agent Programmatically

This shows how to use the components directly without the API.
"""

import os
from pathlib import Path

# Import components
from app.llm_mapper import LLMSchemaMapper
from app.file_reader import read_excel_for_mapping
from app.storage_manager import StorageManager


def example_direct_usage():
    """Example: Using components directly."""
    
    print("=" * 60)
    print("Example: Direct Component Usage")
    print("=" * 60)
    
    # 1. Read an Excel file
    print("\n1. Reading Excel file...")
    file_path = Path("../upload/Tally extract.xlsx")
    
    if not file_path.exists():
        print(f"File not found: {file_path}")
        print("Please update the path to your test file.")
        return
    
    result = read_excel_for_mapping(file_path=str(file_path))
    print(f"   Detected type: {result['detected_type']}")
    print(f"   Columns: {len(result['columns'])}")
    print(f"   Sheets: {result['sheet_names']}")
    
    # 2. Initialize LLM Mapper (requires ANTHROPIC_API_KEY)
    print("\n2. Initializing LLM Mapper...")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("   ⚠️ ANTHROPIC_API_KEY not set. Skipping LLM mapping.")
        print("   Set the environment variable to enable LLM mapping.")
        return
    
    mapper = LLMSchemaMapper(api_key=api_key)
    print("   ✓ LLM Mapper initialized")
    
    # 3. Generate mapping
    print("\n3. Generating schema mapping...")
    mapping_result = mapper.map_columns(
        source_columns=result['columns'],
        sample_data=result['sample_data'],
        file_type=result['detected_type']
    )
    
    print(f"   Overall confidence: {mapping_result.overall_confidence}")
    print(f"   Auto-approve: {mapping_result.auto_approve}")
    print(f"   Unmapped columns: {len(mapping_result.unmapped_columns)}")
    
    # Show some mappings
    print("\n   Sample Mappings:")
    for source, mapping in list(mapping_result.mappings.items())[:5]:
        status = "✓" if mapping.confidence >= 0.85 else "?"
        print(f"   {status} '{source}' → '{mapping.mapped_to}' (confidence: {mapping.confidence:.2f})")
    
    # 4. Save to storage
    print("\n4. Saving to storage...")
    storage = StorageManager(base_storage_path="./storage")
    
    # Extract just the mappings (source -> internal)
    mappings_dict = {
        m.source_column: m.mapped_to
        for m in mapping_result.mappings.values()
        if m.mapped_to != "__unmapped__"
    }
    
    # Extract confidence scores
    confidence_dict = {
        m.source_column: m.confidence
        for m in mapping_result.mappings.values()
    }
    
    saved_path = storage.save_schema_map(
        client_id="HPC_LTD",
        file_type=result['detected_type'],
        mappings=mappings_dict,
        confidence_scores=confidence_dict,
        metadata={
            "source_file": "Tally extract.xlsx",
            "auto_approved": mapping_result.auto_approve
        }
    )
    print(f"   ✓ Saved to: {saved_path}")
    
    # 5. Retrieve the mapping
    print("\n5. Retrieving saved mapping...")
    record = storage.load_schema_map("HPC_LTD", result['detected_type'])
    if record:
        print(f"   Client: {record.client_id}")
        print(f"   File type: {record.file_type}")
        print(f"   Version: {record.version}")
        print(f"   Mappings: {len(record.mappings)}")
    
    # 6. Get mappings as simple dict (for parser agent)
    print("\n6. Getting mappings dict for parser agent...")
    mappings = storage.get_mappings_dict("HPC_LTD", result['detected_type'])
    if mappings:
        print(f"   Mappings ready for parser:")
        for source, internal in list(mappings.items())[:5]:
            print(f"     '{source}' → '{internal}'")
    
    print("\n" + "=" * 60)
    print("Example Complete!")
    print("=" * 60)


def example_with_form26():
    """Example: Processing Form 26 file."""
    
    print("\n" + "=" * 60)
    print("Example: Form 26 Processing")
    print("=" * 60)
    
    file_path = Path("../upload/Form 26 - Deduction Register....xlsx")
    
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    # Read file
    print("\n1. Reading Form 26 file...")
    result = read_excel_for_mapping(file_path=str(file_path))
    print(f"   Detected type: {result['detected_type']}")
    print(f"   Columns: {result['columns'][:10]}")  # Show first 10
    
    # Generate mapping
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("   ⚠️ ANTHROPIC_API_KEY not set. Skipping.")
        return
    
    print("\n2. Generating mapping...")
    mapper = LLMSchemaMapper(api_key=api_key)
    
    mapping_result = mapper.map_columns(
        source_columns=result['columns'],
        sample_data=result['sample_data'],
        file_type="tds"  # Force TDS type
    )
    
    print(f"   Overall confidence: {mapping_result.overall_confidence}")
    print(f"   Auto-approve: {mapping_result.auto_approve}")
    
    print("\n   Key Mappings:")
    key_fields = ['party_name', 'pan', 'tds_section', 'amount_paid', 'tax_deducted']
    for source, mapping in mapping_result.mappings.items():
        if mapping.mapped_to in key_fields:
            print(f"   '{source}' → '{mapping.mapped_to}' (confidence: {mapping.confidence:.2f})")
    
    # Save
    print("\n3. Saving mapping...")
    storage = StorageManager()
    
    mappings_dict = {
        m.source_column: m.mapped_to
        for m in mapping_result.mappings.values()
        if m.mapped_to != "__unmapped__"
    }
    
    saved_path = storage.save_schema_map(
        client_id="HPC_LTD",
        file_type="tds",
        mappings=mappings_dict
    )
    print(f"   ✓ Saved to: {saved_path}")


if __name__ == "__main__":
    # Run examples
    example_direct_usage()
    example_with_form26()
