"""
LLM-Powered Schema Mapper using Groq API (free tier)

This module handles the intelligent mapping of source file columns to internal schema fields.
"""

import json
import os
from typing import Dict, List, Optional, Any
from groq import Groq
from pydantic import BaseModel, Field

from schemas.internal_schemas import (
    get_schema_for_file_type,
    get_all_internal_fields,
    FieldDefinition
)


class ColumnMapping(BaseModel):
    """Single column mapping result"""
    source_column: str
    mapped_to: str  # internal field name or "__unmapped__"
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class SchemaMappingResult(BaseModel):
    """Complete schema mapping result for a file"""
    file_type: str
    source_columns: List[str]
    mappings: Dict[str, ColumnMapping]  # source_column -> ColumnMapping
    unmapped_columns: List[str]
    required_fields_covered: List[str]
    required_fields_missing: List[str]
    overall_confidence: float
    auto_approve: bool = False


class LLMSchemaMapper:
    """
    Schema mapper powered by Groq API (free).

    Maps source file columns to internal schema fields with confidence scores.
    """

    CONFIDENCE_THRESHOLD = 0.85

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"  # Best free model on Groq

    def map_columns(
        self,
        source_columns: List[str],
        sample_data: List[Dict[str, Any]],
        file_type: str,
        past_mappings: Optional[Dict[str, str]] = None
    ) -> SchemaMappingResult:
        internal_schema = get_schema_for_file_type(file_type)

        prompt = self._build_mapping_prompt(
            source_columns=source_columns,
            sample_data=sample_data,
            internal_schema=internal_schema,
            file_type=file_type,
            past_mappings=past_mappings
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000,
        )

        try:
            mapping_json = self._extract_json_from_response(response.choices[0].message.content)
            mappings_data = json.loads(mapping_json)
        except (json.JSONDecodeError, IndexError) as e:
            raise ValueError(f"Failed to parse LLM response: {e}")

        mappings = {}
        unmapped_columns = []

        for item in mappings_data.get("mappings", []):
            source_col = item["source_column"]
            mapping = ColumnMapping(
                source_column=source_col,
                mapped_to=item["mapped_to"],
                confidence=item["confidence"],
                reasoning=item["reasoning"]
            )
            mappings[source_col] = mapping
            if mapping.mapped_to == "__unmapped__":
                unmapped_columns.append(source_col)

        if mappings:
            overall_confidence = sum(m.confidence for m in mappings.values()) / len(mappings)
        else:
            overall_confidence = 0.0

        required_fields = [
            f.name for f in internal_schema.values()
            if f.required and f.name != "pan"
        ]
        covered_fields = set(m.mapped_to for m in mappings.values() if m.mapped_to != "__unmapped__")
        required_fields_covered = [f for f in required_fields if f in covered_fields]
        required_fields_missing = [f for f in required_fields if f not in covered_fields]

        critical_fields = ["date", "party_name", "amount_paid"] if file_type == "tds" else ["date", "party_name", "value"]
        critical_covered = all(f in covered_fields for f in critical_fields)
        auto_approve = overall_confidence >= self.CONFIDENCE_THRESHOLD and critical_covered

        return SchemaMappingResult(
            file_type=file_type,
            source_columns=source_columns,
            mappings=mappings,
            unmapped_columns=unmapped_columns,
            required_fields_covered=required_fields_covered,
            required_fields_missing=required_fields_missing,
            overall_confidence=round(overall_confidence, 2),
            auto_approve=auto_approve
        )

    def _build_mapping_prompt(
        self,
        source_columns: List[str],
        sample_data: List[Dict[str, Any]],
        internal_schema: Dict[str, FieldDefinition],
        file_type: str,
        past_mappings: Optional[Dict[str, str]] = None
    ) -> str:
        internal_fields_text = "\n".join([
            f"  - {name}: {field.description} (type: {field.data_type}, required: {field.required})"
            f"\n    Common source names: {', '.join(field.examples)}"
            for name, field in internal_schema.items()
        ])

        sample_data_text = "\n".join([
            f"Row {i+1}: {json.dumps(row, default=str)}"
            for i, row in enumerate(sample_data[:3])
        ])

        past_mappings_text = ""
        if past_mappings:
            past_mappings_text = f"""
PAST MAPPINGS (from previous similar files):
{json.dumps(past_mappings, indent=2)}

Use these as hints but verify against the actual column names and data.
"""

        return f"""You are a schema mapping expert for TDS (Tax Deducted at Source) reconciliation systems.

Your task is to map columns from a source file to our internal standardized schema fields.

FILE TYPE: {file_type.upper()}

SOURCE FILE COLUMNS:
{json.dumps(source_columns, indent=2)}

SAMPLE DATA (first 3 rows):
{sample_data_text}

{past_mappings_text}

INTERNAL SCHEMA FIELDS (map source columns to these):
{internal_fields_text}

MAPPING RULES:
1. Map each source column to exactly one internal field, or mark as "__unmapped__" if no match
2. Consider column names AND sample data values for accurate mapping
3. Confidence score (0.0-1.0):
   - Exact name match: 0.95-1.0
   - Semantic match with data validation: 0.80-0.94
   - Likely match but uncertain: 0.60-0.79
   - Unclear/no match → map to "__unmapped__"
4. For date fields, look for date values in sample data
5. For amount fields, look for numeric/monetary values
6. For party names, look for vendor/company names
7. PAN fields contain 10-character alphanumeric codes (format: ABCDE1234F)

OUTPUT FORMAT - Return ONLY a valid JSON object, no extra text:
{{
  "mappings": [
    {{
      "source_column": "exact column name from source",
      "mapped_to": "internal_field_name or __unmapped__",
      "confidence": 0.95,
      "reasoning": "brief explanation"
    }}
  ]
}}

Include ALL {len(source_columns)} source columns in the output."""

    def _extract_json_from_response(self, text: str) -> str:
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        else:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return text[start:end]
        return text.strip()
