"""Script/word evidence retaining languages within and across PDF pages."""
import re

VERSION = '2.0.0'
ENGLISH_WORDS = {'the','and','for','is','are','of','in','to','will','with','rain',
                 'weather','district','warning','report','forecast','water','level',
                 'department','expected'}

def detect_language(text):
    letters = [c for c in text if c.isalpha()]
    count = len(letters)
    evidence = []
    if count >= 15:
        for code, first, last in [('si','\u0d80','\u0dff'),('ta','\u0b80','\u0bff')]:
            matched = sum(first <= c <= last for c in letters)
            share = matched / count
            # A short place name or translated heading alone is insufficient.
            if (matched >= 10 and share >= .5) or (matched >= 40 and share >= .15):
                evidence.append(dict(language=code, confidence=round(share,3),
                    letters=matched, share=round(share,3),
                    reason=f'{matched} of {count} alphabetic characters use the {code} script'))
        words = set(re.findall('[a-z]+',text.casefold())) & ENGLISH_WORDS
        latin = sum('a' <= c.lower() <= 'z' for c in letters)
        share = latin / count
        if (share > .75 and len(words) >= 3) or (latin >= 80 and share >= .20 and len(words) >= 5):
            evidence.append(dict(language='en', confidence=round(min(.95,.55+len(words)*.04),3),
                letters=latin, share=round(share,3),
                reason=f'{latin} Latin letters and {len(words)} distinct English function/report words'))
    evidence.sort(key=lambda item:item['language'])
    languages = [item['language'] for item in evidence]
    if len(languages)>1:
        status, reason = 'multilingual', 'Substantial evidence for multiple languages in this text'
    elif languages:
        status, reason = 'single_language', evidence[0]['reason']
    elif count<15:
        status, reason = 'insufficient_text', 'Insufficient extractable alphabetic text; scanned pages may need OCR'
    else:
        status, reason = 'unrecognized_text', 'Text is present but supported-language evidence is insufficient; unsupported language or font encoding may be involved'
    return dict(language='mul' if len(languages)>1 else languages[0] if languages else 'unknown',
        languages_detected=languages, confidence=min((e['confidence'] for e in evidence),default=0.0),
        reason=reason, status=status, evidence=evidence)

def detect_document_languages(pages):
    results = [dict(page=i+1, **detect_language(text)) for i,text in enumerate(pages)]
    languages = sorted({code for page in results for code in page['languages_detected']})
    if len(languages)>1:
        status, reason = 'multilingual', 'Multiple languages detected across PDF pages or within a page; see page evidence'
    elif languages:
        status, reason = 'single_language', 'One supported language detected across PDF pages; see page evidence'
    elif all(p['status']=='insufficient_text' for p in results):
        status, reason = 'insufficient_text', 'Insufficient extractable alphabetic text; scanned pages may need OCR'
    else:
        status, reason = 'unrecognized_text', 'Extracted text has insufficient supported-language evidence; this does not establish that OCR is required'
    best = {code:max(e['confidence'] for p in results for e in p['evidence'] if e['language']==code) for code in languages}
    return dict(version=VERSION, language='mul' if len(languages)>1 else languages[0] if languages else 'unknown',
        languages_detected=languages, confidence=min(best.values(),default=0.0),
        reason=reason, status=status, pages=results)
