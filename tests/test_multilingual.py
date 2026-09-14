import pytest
from scraper.language_detector import detect_language, detect_document_languages
from scraper.normalizer import normalize, validate_alert
from huggingface.build_dataset import to_row, from_row, save_records, read_archive
from tests.test_schema import sample

SI='තද වැසි ඇති විය හැක කොළඹ දිස්ත්‍රික්කය සඳහා අනතුරු ඇඟවීම. '*6
TA='பலத்த மழை பெய்யும் என எதிர்பார்க்கப்படுகிறது யாழ்ப்பாணம் மாவட்டம். '*6
EN='Heavy rain is expected in the Northern province during the next day. '*6

def test_bilingual_pages_are_not_unknown():
    result=detect_document_languages([SI,EN])
    assert result['language']=='mul'
    assert result['languages_detected']==['en','si']
    assert [page['language'] for page in result['pages']]==['si','en']
    assert result['status']=='multilingual'
    assert 'OCR' not in result['reason']

def test_three_scripts_on_one_page_are_retained():
    result=detect_language(SI+TA+EN)
    assert result['language']=='mul'
    assert result['languages_detected']==['en','si','ta']

def test_single_local_script_and_short_english_header():
    result=detect_language('Department of Meteorology\n'+TA)
    assert result['language']=='ta'
    assert result['languages_detected']==['ta']

def test_short_foreign_heading_does_not_label_translation():
    result=detect_language('யாழ்ப்பாணம்\n'+EN)
    assert result['languages_detected']==['en']

def test_blank_and_unrecognized_text_have_distinct_reasons():
    blank=detect_document_languages(['',''])
    unsupported=detect_document_languages(['Bonjour ceci est une prévision du temps avec des nuages. '*20])
    assert blank['status']=='insufficient_text'
    assert unsupported['status']=='unrecognized_text'
    assert blank['languages_detected']==unsupported['languages_detected']==[]
    assert len(blank['pages'])==2

def test_normalization_retains_languages_and_page_evidence():
    row=normalize(sample()['official'],SI+'\f'+EN,'b'*64,'2026-09-14T07:30:00+05:30')
    assert row['languages_detected']==['en','si']
    assert row['language']=='mul'
    assert len(row['extraction']['language_detection']['pages'])==2
    assert row['extraction']['language_detection']['version']=='2.0.0'
    validate_alert(row)

def test_language_lists_roundtrip_through_parquet(tmp_path):
    row=normalize(sample()['official'],SI+'\f'+EN,'b'*64,'2026-09-14T07:30:00+05:30')
    save_records(tmp_path,[row])
    stored=to_row(row)
    assert stored['language_en'] and stored['language_si'] and not stored['language_ta']
    assert read_archive(tmp_path)==[row]

def test_legacy_archive_rows_remain_readable():
    row=to_row(sample())
    row.pop('languages_detected',None)
    for key in ['language_en','language_si','language_ta']: row.pop(key,None)
    assert from_row(row)['language']=='en'
    assert from_row(row)['languages_detected']==['en']

def test_schema_rejects_language_list_inconsistent_with_label():
    row=sample();row['language']='mul';row['languages_detected']=['en']
    with pytest.raises(Exception):validate_alert(row)
