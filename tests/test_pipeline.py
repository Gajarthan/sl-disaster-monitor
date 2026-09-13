from datetime import datetime, timezone
from unittest.mock import patch
import json
from scraper.pipeline import run
from scraper.dmc_scraper import ListingPage
from huggingface.build_dataset import read_archive, save_records
from tests.test_schema import sample

NOW=datetime(2026,9,13,10,tzinfo=timezone.utc)

def test_archive_roundtrip_and_idempotency(tmp_path):
    record=sample()
    save_records(tmp_path,[record]); save_records(tmp_path,[record])
    assert read_archive(tmp_path)==[record]

def test_failure_preserves_previous_feed_and_last_success(tmp_path):
    data=tmp_path/'data'; data.mkdir()
    prior=[sample()]
    (data/'alerts_latest.json').write_text(json.dumps(prior))
    (data/'metadata.json').write_text(json.dumps({'last_successful_scrape':'2026-09-12T10:00:00+00:00'}))
    with patch('scraper.pipeline.fetch_page',side_effect=RuntimeError('DMC unavailable')):
        status=run(tmp_path,now=NOW,pause=0)
    assert status['status']=='error'
    assert status['last_successful_scrape']=='2026-09-12T10:00:00+00:00'
    assert json.loads((data/'alerts_latest.json').read_text())==prior
    assert len(status['errors'])==4

def test_same_pdf_at_multiple_urls_processed_once(tmp_path):
    document=sample()['official']
    docs=[document,dict(document,source_pdf='https://www.dmc.gov.lk/alias.pdf')]
    with patch('scraper.pipeline.fetch_page',return_value=ListingPage(docs,None)), patch('scraper.pipeline.download_pdf',return_value=b'%PDF-test'), patch('scraper.pipeline.extract_text',return_value='Heavy rain is expected in Jaffna district.') as parser:
        first=run(tmp_path,now=NOW,pause=0)
        assert parser.call_count==1
        second=run(tmp_path,now=NOW,pause=0)
        assert parser.call_count==1
    assert first['new_documents']==1
    assert first['duplicate_count']==1
    assert second['new_documents']==0
    assert len(read_archive(tmp_path))==1

def test_failed_download_remains_retryable(tmp_path):
    page=ListingPage([sample()['official']],None)
    with patch('scraper.pipeline.fetch_page',return_value=page),patch('scraper.pipeline.download_pdf',side_effect=ValueError('Download failed')):
        status=run(tmp_path,now=NOW,pause=0)
    assert status['failed_documents']==1
    assert status['download_failures']==1
    assert json.loads((tmp_path/'state/index.json').read_text())=={}

def test_pagination_limit_is_visible(tmp_path):
    with patch('scraper.pipeline.fetch_page',return_value=ListingPage([sample()['official']],20)),patch('scraper.pipeline.download_pdf',return_value=b'%PDF-test'),patch('scraper.pipeline.extract_text',return_value='Heavy rain is expected in Jaffna.'):
        result=run(tmp_path,now=NOW,max_pages=1,pause=0)
    assert result['status']=='partial'
    assert any('page limit' in e for e in result['errors'])

def test_failed_document_is_retried_after_it_leaves_listing(tmp_path):
    document=sample()['official']
    with patch('scraper.pipeline.fetch_page',return_value=ListingPage([document],None)),patch('scraper.pipeline.download_pdf',side_effect=ValueError('offline')):
        run(tmp_path,now=NOW,pause=0)
    with patch('scraper.pipeline.fetch_page',side_effect=RuntimeError('listing outage')),patch('scraper.pipeline.download_pdf',return_value=b'%PDF-test'),patch('scraper.pipeline.extract_text',return_value='Heavy rain in Jaffna district is expected.'):
        result=run(tmp_path,now=NOW,pause=0)
    assert result['new_documents']==1
    assert result['pending_documents']==0

def test_reprocess_can_repair_no_text_without_duplicate_records(tmp_path):
    with patch('scraper.pipeline.fetch_page',return_value=ListingPage([sample()['official']],None)),patch('scraper.pipeline.download_pdf',return_value=b'%PDF-test'),patch('scraper.pipeline.extract_text',return_value='') as parser:
        run(tmp_path,now=NOW,pause=0)
        parser.return_value='Heavy rain is expected in Jaffna district.'
        result=run(tmp_path,now=NOW,pause=0,reprocess=True)
    assert len(read_archive(tmp_path))==1
    assert read_archive(tmp_path)[0]['extraction']['status']=='ok'
    assert result['new_documents']==0

def test_content_duplicates_keep_both_source_listings(tmp_path):
    doc=sample()['official']
    alias=dict(doc,source_pdf='https://www.dmc.gov.lk/alias.pdf')
    with patch('scraper.pipeline.fetch_page',return_value=ListingPage([doc,alias],None)),patch('scraper.pipeline.download_pdf',return_value=b'%PDF-test'),patch('scraper.pipeline.extract_text',return_value='Heavy rain is expected in Jaffna district.'):
        run(tmp_path,now=NOW,pause=0)
    records=read_archive(tmp_path)
    assert len(records)==1
    assert {d['source_pdf'] for d in records[0]['official']['listings']}=={doc['source_pdf'],alias['source_pdf']}

def test_failed_recheck_of_known_url_is_retried_on_normal_run(tmp_path):
    with patch('scraper.pipeline.fetch_page',return_value=ListingPage([sample()['official']],None)),patch('scraper.pipeline.download_pdf',return_value=b'%PDF-test') as download,patch('scraper.pipeline.extract_text',return_value='Heavy rain is expected in Jaffna district.'):
        run(tmp_path,now=NOW,pause=0)
        download.side_effect=ValueError('offline')
        assert run(tmp_path,now=NOW,pause=0,recheck=True)['pending_documents']==1
        download.side_effect=None
        result=run(tmp_path,now=NOW,pause=0)
    assert result['pending_documents']==0
    assert result['status']=='success'

def test_reprocessing_intent_survives_parse_failure(tmp_path):
    with patch('scraper.pipeline.fetch_page',return_value=ListingPage([sample()['official']],None)),patch('scraper.pipeline.download_pdf',return_value=b'%PDF-test'),patch('scraper.pipeline.extract_text',return_value='') as parser:
        run(tmp_path,now=NOW,pause=0)
        parser.side_effect=ValueError('temporary parse failure')
        run(tmp_path,now=NOW,pause=0,reprocess=True)
        parser.side_effect=None
        parser.return_value='Heavy rain is expected in Jaffna district.'
        result=run(tmp_path,now=NOW,pause=0)
    assert read_archive(tmp_path)[0]['extraction']['status']=='ok'
    assert result['pending_documents']==0
