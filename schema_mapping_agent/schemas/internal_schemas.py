"""
Internal Schema Definitions for TDS Reconciliation Pipeline

These are the canonical field names that all source files will be mapped to.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FieldDefinition(BaseModel):
    """Definition of an internal field"""
    name: str
    description: str
    data_type: str = "string"
    required: bool = True
    examples: List[str] = Field(default_factory=list)


# =============================================================================
# TALLY LEDGER INTERNAL SCHEMA
# =============================================================================
TALLY_LEDGER_SCHEMA: Dict[str, FieldDefinition] = {
    "date": FieldDefinition(
        name="date",
        description="Date of the transaction/invoice",
        data_type="date",
        required=True,
        examples=["Date", "Invoice Date", "Transaction Date", "Voucher Date"]
    ),
    "party_name": FieldDefinition(
        name="party_name",
        description="Name of the vendor/supplier/party",
        data_type="string",
        required=True,
        examples=["Particulars", "Party Name", "Vendor Name", "Supplier", "Name"]
    ),
    "voucher_number": FieldDefinition(
        name="voucher_number",
        description="Voucher or invoice number",
        data_type="string",
        required=True,
        examples=["Voucher No.", "Invoice No", "Bill No", "Vch No"]
    ),
    "value": FieldDefinition(
        name="value",
        description="Net value/amount of the transaction (excluding GST)",
        data_type="decimal",
        required=True,
        examples=["Value", "Net Amount", "Taxable Value", "Basic Amount"]
    ),
    "gross_total": FieldDefinition(
        name="gross_total",
        description="Gross total amount including all charges",
        data_type="decimal",
        required=False,
        examples=["Gross Total", "Total Amount", "Gross", "Amount"]
    ),
    "cgst_amount": FieldDefinition(
        name="cgst_amount",
        description="Central GST amount",
        data_type="decimal",
        required=False,
        examples=["Input C GST", "CGST", "C GST", "Central GST"]
    ),
    "sgst_amount": FieldDefinition(
        name="sgst_amount",
        description="State GST amount",
        data_type="decimal",
        required=False,
        examples=["Input S GST", "SGST", "S GST", "State GST"]
    ),
    "igst_amount": FieldDefinition(
        name="igst_amount",
        description="Integrated GST amount",
        data_type="decimal",
        required=False,
        examples=["Input I GST", "IGST", "I GST", "Integrated GST"]
    ),
    "tds_amount": FieldDefinition(
        name="tds_amount",
        description="TDS amount deducted",
        data_type="decimal",
        required=False,
        examples=["TDS", "Tax Deducted", "TDS Amount", "TDS Deducted"]
    ),
    "tds_section": FieldDefinition(
        name="tds_section",
        description="TDS section code (e.g., 194C, 194J, 194H)",
        data_type="string",
        required=False,
        examples=["Section", "TDS Section", "Section Code"]
    ),
    "pan": FieldDefinition(
        name="pan",
        description="PAN number of the party",
        data_type="string",
        required=False,
        examples=["PAN", "PAN No", "Permanent Account Number"]
    ),
    "gstin": FieldDefinition(
        name="gstin",
        description="GSTIN of the party",
        data_type="string",
        required=False,
        examples=["GSTIN", "GST No", "GST Number"]
    ),
    "expense_type": FieldDefinition(
        name="expense_type",
        description="Type of expense or purchase account",
        data_type="string",
        required=False,
        examples=["Purchase Account", "Expense Type", "Account"]
    ),
}


# =============================================================================
# FORM 26AS / TDS CERTIFICATE INTERNAL SCHEMA
# =============================================================================
FORM26_TDS_SCHEMA: Dict[str, FieldDefinition] = {
    "party_name": FieldDefinition(
        name="party_name",
        description="Name of the deductee/party with PAN",
        data_type="string",
        required=True,
        examples=["Name", "Deductee Name", "Party", "Vendor Name"]
    ),
    "pan": FieldDefinition(
        name="pan",
        description="PAN number of the party",
        data_type="string",
        required=True,
        examples=["PAN", "PAN No", "Permanent Account Number"]
    ),
    "tds_section": FieldDefinition(
        name="tds_section",
        description="TDS section code (194C, 194J, 194H, 194A, 194Q, etc.)",
        data_type="string",
        required=True,
        examples=["Section", "TDS Section", "Section Code"]
    ),
    "amount_paid": FieldDefinition(
        name="amount_paid",
        description="Amount paid/credited to the party",
        data_type="decimal",
        required=True,
        examples=["Amt. Paid/Crdt/Drawn Rs.", "Amount Paid", "Credit Amount", "Paid Amount"]
    ),
    "date_of_payment": FieldDefinition(
        name="date_of_payment",
        description="Date when amount was paid/credited",
        data_type="date",
        required=True,
        examples=["Amt. Paid/Crdt/Drawn Date", "Payment Date", "Date of Credit"]
    ),
    "income_tax": FieldDefinition(
        name="income_tax",
        description="Income tax amount deducted",
        data_type="decimal",
        required=True,
        examples=["Income Tax Rs.", "Tax Amount", "TDS Amount"]
    ),
    "surcharge": FieldDefinition(
        name="surcharge",
        description="Surcharge on TDS",
        data_type="decimal",
        required=False,
        examples=["Surcharge Rs.", "Surcharge"]
    ),
    "cess": FieldDefinition(
        name="cess",
        description="Health and Education Cess",
        data_type="decimal",
        required=False,
        examples=["Cess Rs.", "Cess", "Education Cess"]
    ),
    "tax_rate": FieldDefinition(
        name="tax_rate",
        description="TDS tax rate percentage",
        data_type="decimal",
        required=True,
        examples=["Tax Rate %", "Rate", "TDS Rate", "Percentage"]
    ),
    "tax_deducted": FieldDefinition(
        name="tax_deducted",
        description="Total tax deducted (Income Tax + Surcharge + Cess)",
        data_type="decimal",
        required=True,
        examples=["Tax Deducted Rs.", "Total TDS", "Tax Deducted"]
    ),
    "date_of_deduction": FieldDefinition(
        name="date_of_deduction",
        description="Date when TDS was deducted",
        data_type="date",
        required=True,
        examples=["Tax Deducted Date", "Deduction Date", "TDS Date"]
    ),
    "certificate_number": FieldDefinition(
        name="certificate_number",
        description="TDS certificate number (Form 16A/26AS reference)",
        data_type="string",
        required=False,
        examples=["Certificate No", "Challan No", "Reference No"]
    ),
    "non_deduction_reason": FieldDefinition(
        name="non_deduction_reason",
        description="Reason if TDS was not deducted",
        data_type="string",
        required=False,
        examples=["Non Deduction Reason", "Reason", "Remarks"]
    ),
}


def get_schema_for_file_type(file_type: str) -> Dict[str, FieldDefinition]:
    """
    Get the internal schema for a given file type.
    
    Args:
        file_type: Either 'ledger' or 'tds' (for Form 26AS/TDS data)
    
    Returns:
        Dictionary of field definitions
    """
    file_type = file_type.lower()
    if file_type in ["ledger", "tally", "purchase"]:
        return TALLY_LEDGER_SCHEMA
    elif file_type in ["tds", "form26", "form26as", "26as", "tds_certificate"]:
        return FORM26_TDS_SCHEMA
    else:
        raise ValueError(f"Unknown file_type: {file_type}. Use 'ledger' or 'tds'")


def get_all_internal_fields(file_type: str) -> List[str]:
    """Get list of all internal field names for a file type"""
    schema = get_schema_for_file_type(file_type)
    return list(schema.keys())


def get_field_description(field_name: str, file_type: str) -> Optional[str]:
    """Get description for a specific internal field"""
    schema = get_schema_for_file_type(file_type)
    if field_name in schema:
        return schema[field_name].description
    return None
