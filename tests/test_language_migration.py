from unittest.mock import patch
from pathlib import Path
from scraper.reprocess_languages import reprocess_languages
from huggingface.build_dataset import read_archive,save_records
from scraper.deduplicate import content_hash
from tests.test_schema import sample
from tests.test_multilingual import SI,EN

def old_record():
    record=sample()
    record['content_hash']=content_hash(b'%PDF-test');record['id']='dmc-'+record['content_hash']
    record['language']='unknown';record['languages_detected']=[]
    record['extraction'].pop('language_detection',None)
    return record

def test_language_migration_preserves_source_and_other_extractions(tmp_path):
    old=old_record();save_records(tmp_path,[old])
    with patch('scraper.reprocess_languages.download_pdf',return_value=b'%PDF-test'),patch('scraper.reprocess_languages.extract_text',return_value=SI+'\f'+EN):
        result=reprocess_languages(tmp_path,pause=0)
        again=reprocess_languages(tmp_path,pause=0)
    new=read_archive(tmp_path)[0]
    assert new['language']=='mul' and new['languages_detected']==['en','si']
    assert result['updated']==1 and again['updated']==0
    for key in ['official','hazard','hazards','severity','summary','districts','provinces','id','content_hash','issued_at']:
        assert new[key]==old[key]

def test_replaced_pdf_cannot_change_old_record_language(tmp_path):
    old=old_record();save_records(tmp_path,[old])
    with patch('scraper.reprocess_languages.download_pdf',return_value=b'%PDF-replaced'):
        result=reprocess_languages(tmp_path,pause=0)
    assert result['failed']==1
    assert read_archive(tmp_path)[0]==old
