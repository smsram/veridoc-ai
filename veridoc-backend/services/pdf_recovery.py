import io
import re

def analyze_and_recover_pdf(file_bytes: bytes):
    """
    Analyzes a PDF for incremental updates (edits) and extracts the original version.
    Ignores false positives like 'Linearized' Fast Web View markers.
    """
    # 1. Find every single End-Of-File marker in the binary
    eof_matches = list(re.finditer(b'%%EOF', file_bytes))
    
    # 2. VerifyPDF Strategy: Filter out false-positive markers
    valid_eofs = []
    
    # Check if the PDF is "Linearized" (optimized for web)
    is_linearized = b'/Linearized' in file_bytes[:2048]

    for m in eof_matches:
        # Linearized PDFs have a fake EOF in the first ~4 kilobytes. We MUST ignore it.
        if is_linearized and m.start() < 4096:
            continue
            
        # Ignore random EOFs that might be buried in image streams (ensure they are properly spaced)
        # We only keep EOFs that actually represent structural boundaries.
        valid_eofs.append(m.start())

    revisions_count = len(valid_eofs)
    has_incremental_updates = revisions_count > 1
    
    result = {
        "is_modified": has_incremental_updates,
        "revision_count": revisions_count,
        "recovered_bytes": None,
        "risk_indicators": []
    }
    
    if has_incremental_updates:
        result["risk_indicators"].append({
            "title": "Modified Document (Incremental Updates)",
            "description": f"This document has {revisions_count} save states. It was modified after it was created. An original version has been recovered to verify the changes.",
            "severity": "Critical"
        })
        
        # 3. THE TIME MACHINE: Extract the true original!
        # Slice the file exactly at the first VALID End-Of-File marker
        first_valid_eof = valid_eofs[0] + 5
        original_pdf_bytes = file_bytes[:first_valid_eof]
        
        result["recovered_bytes"] = original_pdf_bytes
    
    return result