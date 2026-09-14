from pathlib import Path
import pytest
from scraper.dmc_scraper import parse_listing, ListingError, category_url
from scraper.pdf_parser import extract_text, PDFError

FIXTURES = Path(__file__).parent / 'fixtures'

def test_real_dmc_table_extracts_fields_and_pagination():
    page = parse_listing((FIXTURES/'listing.html').read_text(), category_url('weather'), 'weather')
    assert len(page.documents) == 2
    row = page.documents[0]
    assert row['title'] == 'Heavy Rain Advisory'
    assert row['report_date'] == '2026-09-13'
    assert row['report_time'] == '14:00'
    assert row['source_pdf'] == 'https://www.dmc.gov.lk/images/dmcreports/rain.pdf'
    assert page.next_offset == 2

def test_missing_table_is_failure_not_empty():
    with pytest.raises(ListingError):
        parse_listing('<html>Maintenance</html>', category_url('weather'), 'weather')

def test_invalid_row_surfaces_failure():
    html = (FIXTURES/'listing.html').read_text().replace('2026-09-13','not-a-date')
    with pytest.raises(ListingError):
        parse_listing(html, category_url('weather'), 'weather')

def test_external_pdf_is_rejected():
    html = (FIXTURES/'listing.html').read_text().replace('/images/dmcreports/rain.pdf','https://evil.example/rain.pdf')
    with pytest.raises(ListingError):
        parse_listing(html, category_url('weather'), 'weather')

def test_bad_pdf_is_explicit_error(tmp_path):
    path = tmp_path/'broken.pdf'
    path.write_bytes(b'<html>error</html>')
    with pytest.raises(PDFError):
        extract_text(path)

def test_image_only_pdf_returns_no_text(tmp_path):
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=100,height=100)
    path = tmp_path/'blank.pdf'
    writer.write(path)
    assert extract_text(path) == ''

def test_pdf_text_preserves_page_boundaries_including_blank_pages(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer=PdfWriter()
    for text in ['First page weather report','','Second page weather report']:
        page=writer.add_blank_page(width=200,height=200)
        if text:
            font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
            stream=DecodedStreamObject();stream.set_data(f'BT /F1 12 Tf ({text}) Tj ET'.encode())
            page[NameObject('/Contents')]=stream
    path=tmp_path/'pages.pdf';writer.write(path)
    assert extract_text(path).split('\f')==['First page weather report','','Second page weather report']
