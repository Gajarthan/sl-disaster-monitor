"""Upgrade archived language evidence without changing other extracted fields."""
import argparse
from datetime import datetime,timezone
import logging
from pathlib import Path
import tempfile
import time
from .deduplicate import content_hash
from .dmc_scraper import session
from .language_detector import VERSION,detect_document_languages
from .normalizer import validate_alert
from .pdf_parser import extract_text
from .pipeline import download_pdf,publish_feeds
from .storage import read_json,write_json
from huggingface.build_dataset import read_archive,save_records

LOG=logging.getLogger(__name__)

def reprocess_languages(root, *, pause=.4):
    root=Path(root)
    records=read_archive(root)
    now=datetime.now(timezone.utc)
    status={'version':VERSION,'run_at':now.isoformat(),'checked':len(records),'updated':0,'failed':0,'errors':[]}
    additions=[]
    with session() as client:
        for original in records:
            if original['extraction'].get('language_detection',{}).get('version')==VERSION:
                continue
            try:
                LOG.info('Language extraction: %s',original['source_pdf'])
                content=download_pdf(client,original['source_pdf'])
                if content_hash(content)!=original['content_hash']:
                    raise ValueError('Source PDF has changed; cannot rewrite evidence for the archived content hash')
                with tempfile.TemporaryDirectory(prefix='dmc-language-') as directory:
                    path=Path(directory)/'report.pdf';path.write_bytes(content)
                    text=extract_text(path)
                detection=detect_document_languages(text.split('\f'))
                record=dict(original,language=detection['language'],languages_detected=detection['languages_detected'],
                    language_confidence=detection['confidence'],language_reason=detection['reason'],
                    processed_at=now.isoformat(),extraction=dict(original['extraction'],language_detection=detection))
                validate_alert(record)
                additions.append(record)
                status['updated']+=1
            except Exception as exc:
                status['failed']+=1
                status['errors'].append({'id':original['id'],'source_pdf':original['source_pdf'],'error':str(exc)})
                LOG.error('%s: %s',original['id'],exc)
            time.sleep(pause)
    save_records(root,additions)
    current=read_archive(root)
    if additions:
        publish_feeds(root,current,now)
        metadata=read_json(root/'data/metadata.json',{})
        metadata.update(language_reprocessed_at=now.isoformat(),language_detector_version=VERSION,
            multilingual_documents_total=sum(r['language']=='mul' for r in current),
            unknown_language_total=sum(r['language']=='unknown' for r in current),
            extraction_incomplete_total=sum(r['language']=='unknown' or r['extraction']['status']!='ok' for r in current))
        write_json(root/'data/metadata.json',metadata)
    status['status']='success' if not status['failed'] else 'partial'
    # Failures remain visible and retryable: unchanged records lack this version.
    write_json(root/'state/language_migration.json',status)
    return status

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    result=reprocess_languages(args.root)
    print({k:v for k,v in result.items() if k!='errors'})
    raise SystemExit(0 if result['status']=='success' else 1)
