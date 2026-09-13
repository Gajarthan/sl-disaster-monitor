import copy
import pytest
from scraper.normalizer import normalize, validate_alert

def sample():
    return normalize({'title':'Heavy Rain Advisory','description':'','report_date':'2026-09-13','report_time':'14:00','document_type':'weather','source_page':'https://www.dmc.gov.lk/index.php','source_pdf':'https://www.dmc.gov.lk/images/test.pdf'},'Heavy rain is expected in Jaffna district.','a'*64,'2026-09-13T15:00:00+05:30')

def test_normalized_record_keeps_source_and_extraction_separate():
    alert=sample()
    validate_alert(alert)
    assert alert['issued_at']=='2026-09-13T14:00:00+05:30'
    assert alert['valid_until'] is None
    assert alert['districts']==['Jaffna']
    assert alert['official']['title']=='Heavy Rain Advisory'
    assert alert['extraction']['location_scope']=='mentions'

def test_schema_rejects_invalid_severity_and_url():
    for key,value in [('severity','emergency'),('source_pdf','javascript:alert(1)'),('issued_at','yesterday')]:
        alert=copy.deepcopy(sample()); alert[key]=value
        with pytest.raises(Exception): validate_alert(alert)

def test_no_text_does_not_claim_english_from_listing_title():
    alert=normalize({'title':'Weather Forecast','report_date':'2026-09-13','report_time':'','description':'','document_type':'weather','source_page':'https://www.dmc.gov.lk/index.php','source_pdf':'https://www.dmc.gov.lk/a.pdf'},'', 'b'*64,'2026-09-13T15:00:00+05:30')
    assert alert['language']=='unknown'
    assert alert['issued_at'] is None
    assert alert['extraction']['status']=='no_text'
