import re

def detect_severity(title, text):
    # A generic warning legend or historical table in body text is not an issued level.
    # Only explicit listing-title labels are normalized in v1.
    title = title.casefold()
    rules = [('severe',r'\bred alert\b|\blevel\s*3\b'),
             ('advisory',r'\badvisory\b|\badvice\b|ஆலோசனை'),
             ('warning',r'\bwarning\b|எச்சரிக்கை|අනතුරු ඇඟවීම'),
             ('info',r'\bforecast\b|\bsituation report\b|\bsituation summary\b')]
    for severity, pattern in rules:
        match = re.search(pattern,title)
        if match:
            return dict(severity=severity,evidence=match.group(0),reason='Explicit label in official listing title')
    return dict(severity='unknown',evidence='',reason='No unambiguous issued severity label in listing title')
