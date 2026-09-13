import pytest
from scraper.language_detector import detect_language

@pytest.mark.parametrize('text,language',[
    ('பலத்த மழை பெய்யும் என எதிர்பார்க்கப்படுகிறது யாழ்ப்பாணம் மாவட்டம்','ta'),
    ('තද වැසි ඇති විය හැක කොළඹ දිස්ත්‍රික්කය සඳහා අනතුරු ඇඟවීම','si'),
    ('Heavy rain is expected in the Northern province during the next day.','en'),
    ('1234 / ???','unknown'), ('','unknown'),
    ('Bonjour ceci est une prévision du temps avec des nuages','unknown'),
])
def test_language(text,language):
    result=detect_language(text)
    assert result['language']==language
    assert 0 <= result['confidence'] <= 1
    assert result['reason']

def test_english_header_does_not_hide_tamil_body():
    assert detect_language('Department of Meteorology\n'+'பலத்த மழை பெய்யும் என எதிர்பார்க்கப்படுகிறது '*10)['language']=='ta'

def test_minor_local_script_does_not_claim_dominance():
    text='The weather report for the district is expected today. '*10+'பலத்த மழை '*15
    assert detect_language(text)['language']!='ta'
