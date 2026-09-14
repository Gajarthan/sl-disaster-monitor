from datetime import datetime, timezone, timedelta
import re
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from .language_detector import detect_document_languages
from .district_detector import detect_locations
from .hazard_detector import detect_hazards
from .severity_detector import detect_severity

TZ = timezone(timedelta(hours=5,minutes=30))
RULES_VERSION = '1.1.0'

def normalize(document, text, digest, processed_at):
    language = detect_document_languages(text.split('\f'))
    locations = detect_locations(text)
    title_hazards = detect_hazards(document['title'])
    hazards = list(dict.fromkeys(title_hazards + detect_hazards(text)))
    specific=[h for h in hazards if h not in ('other','general_weather')]
    hazards=specific or (['general_weather'] if 'general_weather' in hazards else ['other'])
    severity = detect_severity(document['title'],text)
    issued = None
    if document.get('report_time'):
        issued = datetime.strptime(document['report_date']+' '+document['report_time'],'%Y-%m-%d %H:%M').replace(tzinfo=TZ).isoformat()
    summary = re.sub(r'\s+',' ',text).strip()[:600]
    alert = dict(id='dmc-'+digest, source='DMC', document_type=document['document_type'],
        hazard=hazards[0], hazards=hazards, severity=severity['severity'],title=document['title'],
        description=document.get('description',''),summary=summary,language=language['language'],
        languages_detected=language['languages_detected'],
        language_confidence=language['confidence'], language_reason=language['reason'],issued_at=issued,
        valid_from=None,valid_until=None, **locations,source_page=document['source_page'],source_pdf=document['source_pdf'],
        content_hash=digest,processed_at=processed_at, official=dict(document),
        extraction=dict(rules_version=RULES_VERSION,status='ok' if text.strip() else 'no_text',
          language_detection=language,
          location_scope='mentions',severity_evidence=severity['evidence'],severity_reason=severity['reason'],
          summary_method='first_600_characters_of_extracted_text',validity_reason='Not inferred by MVP rules'))
    validate_alert(alert)
    return alert

def validate_alert(alert):
    schema=json.loads((Path(__file__).resolve().parents[1]/'schemas/alert.schema.json').read_text())
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(alert)
    languages=alert['languages_detected']
    expected='mul' if len(languages)>1 else languages[0] if languages else 'unknown'
    if alert['language']!=expected: raise ValueError('Language label must agree with languages_detected')

    for field in ('issued_at','valid_from','valid_until','processed_at'):
        if alert[field] is not None:
            parsed = datetime.fromisoformat(alert[field])
            if parsed.tzinfo is None: raise ValueError(f'{field} requires timezone')
