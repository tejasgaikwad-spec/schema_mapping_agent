"""
Excel File Reader for Schema Mapping

Handles reading XLSX files and extracting headers + sample data.
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import io


class ExcelFileReader:
    """Reader for Excel files to extract schema information."""
    
    def __init__(self, file_path: Optional[str] = None, file_bytes: Optional[bytes] = None):
        """
        Initialize with either a file path or file bytes.
        
        Args:
            file_path: Path to the Excel file
            file_bytes: Raw bytes of the Excel file (for uploaded files)
        """
        self.file_path = file_path
        self.file_bytes = file_bytes
        
        if not file_path and not file_bytes:
            raise ValueError("Either file_path or file_bytes must be provided")
    
    def get_sheet_names(self) -> List[str]:
        """Get list of sheet names in the Excel file."""
        if self.file_bytes:
            xl = pd.ExcelFile(io.BytesIO(self.file_bytes))
        else:
            xl = pd.ExcelFile(self.file_path)
        return xl.sheet_names
    
    def read_sheet(
        self, 
        sheet_name: Optional[str] = None, 
        sheet_index: int = 0,
        header_row: Optional[int] = None,
        skip_rows: int = 0
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Read a sheet and return column headers and sample data.
        
        Args:
            sheet_name: Name of the sheet to read (None for first sheet)
            sheet_index: Index of sheet if sheet_name not provided
            header_row: Row index containing headers (None for auto-detect)
            skip_rows: Number of rows to skip at the beginning
            
        Returns:
            Tuple of (column_names, sample_data)
        """
        # Read the Excel file
        if self.file_bytes:
            source = io.BytesIO(self.file_bytes)
        else:
            source = self.file_path
        
        # Try to detect header row if not specified
        if header_row is None:
            header_row = self._detect_header_row(source, sheet_name or sheet_index)
        
        # Read the data
        df = pd.read_excel(
            source,
            sheet_name=sheet_name or sheet_index,
            header=header_row,
            skiprows=skip_rows,
            nrows=5  # Read only first 5 rows for sample
        )
        
        # Clean column names
        df.columns = [str(col).strip() if pd.notna(col) else f"Unnamed: {i}" 
                      for i, col in enumerate(df.columns)]
        
        # Get column names
        columns = list(df.columns)
        
        # Get sample data (first 3 rows)
        sample_data = df.head(3).to_dict('records')
        
        # Clean sample data (convert NaN to None, dates to strings)
        cleaned_samples = []
        for row in sample_data:
            cleaned_row = {}
            for key, value in row.items():
                if pd.isna(value):
                    cleaned_row[key] = None
                elif isinstance(value, pd.Timestamp):
                    cleaned_row[key] = value.strftime('%Y-%m-%d')
                else:
                    cleaned_row[key] = value
            cleaned_samples.append(cleaned_row)
        
        return columns, cleaned_samples
    
    def _detect_header_row(self, source, sheet_ref, max_rows: int = 10) -> int:
        """
        Attempt to detect which row contains the headers.
        
        Heuristics:
        - Row with most non-null string values
        - Row that looks like column names (not dates, not pure numbers)
        """
        df_preview = pd.read_excel(
            source,
            sheet_name=sheet_ref,
            header=None,
            nrows=max_rows
        )
        
        best_row = 0
        best_score = 0
        
        for idx, row in df_preview.iterrows():
            score = 0
            for val in row:
                if pd.notna(val):
                    val_str = str(val).strip()
                    # Prefer rows with string values that look like headers
                    if val_str and not val_str.replace('.', '').isdigit():
                        # Check if it looks like a date
                        try:
                            pd.to_datetime(val_str)
                            # It's a date, less likely to be a header
                            score += 0.5
                        except:
                            # Likely a header
                            score += 2
            
            if score > best_score:
                best_score = score
                best_row = idx
        
        return best_row
    
    def detect_file_type(self, sheet_name: Optional[str] = None) -> str:
        """
        Attempt to detect if this is a Tally ledger or Form 26 TDS file.
        
        Returns:
            'ledger' or 'tds'
        """
        columns, sample_data = self.read_sheet(sheet_name)
        columns_lower = [c.lower() for c in columns]
        columns_text = ' '.join(columns_lower)
        
        # TDS/Form 26 indicators
        tds_indicators = [
            'section', 'tds', 'tax deducted', 'income tax', 'cess', 
            'surcharge', 'tax rate', '26as', 'form 26', 'deduction'
        ]
        
        # Tally/Ledger indicators
        ledger_indicators = [
            'voucher', 'particulars', 'purchase', 'gst', 'cgst', 'sgst',
            'igst', 'gross total', 'net amount', 'invoice'
        ]
        
        tds_score = sum(1 for ind in tds_indicators if ind in columns_text)
        ledger_score = sum(1 for ind in ledger_indicators if ind in columns_text)
        
        return 'tds' if tds_score > ledger_score else 'ledger'


def read_excel_for_mapping(
    file_path: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to read an Excel file for schema mapping.
    
    Returns:
        Dict with 'columns', 'sample_data', 'sheet_names', 'detected_type'
    """
    reader = ExcelFileReader(file_path=file_path, file_bytes=file_bytes)
    
    sheet_names = reader.get_sheet_names()
    columns, sample_data = reader.read_sheet(sheet_name=sheet_name)
    detected_type = reader.detect_file_type(sheet_name=sheet_name)
    
    return {
        'columns': columns,
        'sample_data': sample_data,
        'sheet_names': sheet_names,
        'detected_type': detected_type
    }
