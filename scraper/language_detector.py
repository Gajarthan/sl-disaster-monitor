"""Script proportions with conservative English evidence; no external API."""
import re

def detect_language(text):
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 15:
        return dict(language='unknown',confidence=0.0,reason='Insufficient extractable alphabetic text')
    counts = {'ta':sum('\u0b80' <= c <= '\u0bff' for c in letters),
              'si':sum('\u0d80' <= c <= '\u0dff' for c in letters)}
    lang = max(counts,key=counts.get)
    ratio = counts[lang]/len(letters)
    if counts[lang] >= 10 and ratio >= .5:
        return dict(language=lang,confidence=round(ratio,3),reason=f'{counts[lang]} of {len(letters)} letters use the {lang} Unicode script; dominant local script')
    words = set(re.findall('[a-z]+',text.lower()))
    evidence = words & {'the','and','for','is','are','of','in','to','will','with','rain','weather','district','warning','report','forecast','water','level','department','expected'}
    latin = sum('a' <= c.lower() <= 'z' for c in letters)/len(letters)
    if latin > .75 and len(evidence) >= 3:
        return dict(language='en',confidence=round(min(.95, .55+len(evidence)*.04),3),reason='Predominantly Latin letters with multiple English function/weather words')
    return dict(language='unknown',confidence=0.0,reason='No supported script/language has sufficient evidence; legacy PDF fonts may need OCR')
