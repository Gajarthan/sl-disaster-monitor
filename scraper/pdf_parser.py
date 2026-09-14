from pathlib import Path
from pypdf import PdfReader

class PDFError(ValueError):
    pass

def extract_text(path: Path):
    try:
        with path.open('rb') as stream:
            if stream.read(5) != b'%PDF-':
                raise PDFError('Response is not a PDF')
            stream.seek(0)
            reader = PdfReader(stream, strict=False)
            if reader.is_encrypted:
                raise PDFError('Encrypted PDF')
            if len(reader.pages) > 150:
                raise PDFError('PDF exceeds 150 page processing limit')
            # Form-feed preserves real page boundaries, including blank pages.
            text = '\f'.join((page.extract_text() or '').replace('\f','\n').replace('\x00','').strip() for page in reader.pages)
            if len(text) > 2_000_000:
                raise PDFError('Extracted text exceeds limit')
            return text
    except PDFError:
        raise
    except Exception as exc:
        raise PDFError(f'PDF extraction failed: {type(exc).__name__}') from exc
