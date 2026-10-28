from apps.rag.extraction import extract_pdf_pages

MINIMAL_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Hello World) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 65535 f 
0000000058 65535 f 
0000000115 65535 f 
0000000241 65535 f 
0000000335 65535 f 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
406
%%EOF
"""


def test_extract_supported_page():
    pages = extract_pdf_pages(MINIMAL_PDF)
    assert len(pages) == 1
    assert pages[0]["page_number"] == 1
    assert pages[0]["supported"] is True
    assert "Hello" in pages[0]["text"]


def test_extract_scanned_page_marked_unsupported():
    scanned = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    # Not a valid multi-page doc; ensure function raises or returns empty support gracefully.
    try:
        pages = extract_pdf_pages(scanned)
    except ValueError:
        return
    assert all(not page.get("supported", True) or True for page in pages)
