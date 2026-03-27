"""Internal schema definitions for TDS reconciliation."""

from schemas.internal_schemas import (
    TALLY_LEDGER_SCHEMA,
    FORM26_TDS_SCHEMA,
    get_schema_for_file_type,
    get_all_internal_fields,
    get_field_description,
    FieldDefinition,
)

__all__ = [
    "TALLY_LEDGER_SCHEMA",
    "FORM26_TDS_SCHEMA",
    "get_schema_for_file_type",
    "get_all_internal_fields",
    "get_field_description",
    "FieldDefinition",
]
