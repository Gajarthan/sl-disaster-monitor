"""Collect each category independently, preserve prior good data, publish health."""
import argparse
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import tempfile
import time
from .dmc_scraper import CATEGORIES, category_url, parse_listing, get_response, session
from .deduplicate import content_hash
from .pdf_parser import extract_text, PDFError
from .normalizer import normalize
from .storage import read_json, write_json
from huggingface.build_dataset import read_archive, save_records

LOG=logging.getLogger(__name__)
MAX_PDF_BYTES=20*1024*1024

def merge_listings(record, listings):
    official=record['official']
    saved=official.setdefault('listings',[{k:v for k,v in official.items() if k!='listings'}])
    identity=lambda d:tuple(d.get(k,'') for k in ('source_pdf','document_type','title','report_date','report_time'))
    seen={identity(d) for d in saved}
    for listing in listings:
        if identity(listing) not in seen:
            saved.append(dict(listing)); seen.add(identity(listing))

def fetch_page(client, url, category):
    with get_response(client,url) as response:
        if len(response.content)>3_000_000: raise ValueError('Listing exceeds size limit')
        return parse_listing(response.text,url,category)

def download_pdf(client,url):
    with get_response(client,url,stream=True) as response:
        chunks=[]; size=0
        for chunk in response.iter_content(65536):
            size+=len(chunk)
            if size>MAX_PDF_BYTES: raise ValueError('PDF exceeds 20 MB limit')
            chunks.append(chunk)
        content=b''.join(chunks)
        if not content.startswith(b'%PDF-'): raise ValueError('DMC download did not return a PDF')
        return content

def publish_feeds(root, records, now):
    def recent(record,days):
        stamp=record['issued_at']
        if not stamp: return False
        issued=datetime.fromisoformat(stamp)
        return now-timedelta(days=days)<=issued<=now+timedelta(minutes=15)
    ordered=sorted(records,key=lambda r:(r['issued_at'] or '',r['id']),reverse=True)
    latest=[r for r in ordered if recent(r,3)]
    recent_rows=[r for r in ordered if recent(r,30)]
    for name,rows in {'alerts_latest':latest,'alerts_recent':recent_rows,
        'weather':[r for r in latest if r['document_type']=='weather'],
        'floods':[r for r in latest if any(h in r['hazards'] for h in ['flood','river_flood'])],
        'landslides':[r for r in latest if 'landslide' in r['hazards']]}.items():
        write_json(Path(root)/'data'/f'{name}.json',rows)

def run(root, *, now=None, max_pages=20, bootstrap_days=7, pause=.4, client=None, recheck=False, reprocess=False):
    root=Path(root); now=now or datetime.now(timezone.utc); stamp=now.isoformat()
    previous=read_json(root/'data/metadata.json',{})
    index=read_json(root/'state/index.json',{})
    pending=read_json(root/'state/pending.json',{})
    records=read_archive(root)
    by_hash={r['content_hash']:r for r in records}
    status=dict(last_run=stamp,status='error',last_successful_scrape=previous.get('last_successful_scrape'),
        last_dmc_document_seen=previous.get('last_dmc_document_seen'),documents_checked=0,new_documents=0,
        failed_documents=0,download_failures=0,parsing_failures=0,duplicate_count=0,unknown_language_count=0,
        no_text_count=0,reprocessed_documents=0,errors=[],category_status={},coverage_days=bootstrap_days,
        latest_window_hours=72,recent_window_days=30)
    owned_client=client is None
    client=client or session()
    discovered={}
    occurrences={}
    category_success=0
    for category in CATEGORIES:
        offset=0; seen_pages=set(); category_docs=0
        try:
            for page_number in range(max_pages):
                url=category_url(category,offset)
                LOG.info('Listing %s page %d',category,page_number+1)
                page=fetch_page(client,url,category)
                signature=tuple(d['source_pdf'] for d in page.documents)
                if signature in seen_pages: raise ValueError('DMC pagination repeated a page')
                seen_pages.add(signature)
                category_docs+=len(page.documents)
                known_page=all(d['source_pdf'] in index for d in page.documents)
                for doc in page.documents:
                    discovered.setdefault(doc['source_pdf'],doc)
                    occurrences.setdefault(doc['source_pdf'],[]).append(doc)
                # Always inspect the next page before trusting a known-page boundary.
                oldest=min(d['report_date'] for d in page.documents)
                cutoff=(now-timedelta(days=bootstrap_days)).date().isoformat()
                if page.next_offset is None or oldest<cutoff or (known_page and page_number>=1 and not reprocess):
                    break
                if page_number+1==max_pages: raise ValueError('Reached page limit before archive/age boundary; increase --max-pages')
                if page.next_offset<=offset: raise ValueError('Pagination did not advance')
                offset=page.next_offset
                time.sleep(pause)
            category_success+=1
            status['category_status'][category]={'status':'success','documents_checked':category_docs}
        except Exception as exc:
            message=f'{category}: {type(exc).__name__}: {exc}'
            LOG.error(message); status['errors'].append(message)
            status['category_status'][category]={'status':'error','documents_checked':category_docs,'error':str(exc)}
    status['documents_checked']=len(discovered)
    seen_dates=[d['report_date']+'T'+(d['report_time'] or '00:00')+':00+05:30' for d in discovered.values()]
    if seen_dates:
        status['last_dmc_document_seen']=max(seen_dates+[previous.get('last_dmc_document_seen') or ''])
    for url,entry in pending.items(): discovered.setdefault(url,entry['document'])
    additions=[]
    processed_hashes=set()
    for url,doc in discovered.items():
        force_parse=reprocess or pending.get(url,{}).get('reprocess',False)
        if url in index and url not in pending and not recheck and not reprocess:
            existing=by_hash.get(index[url]['hash'])
            if existing is not None:
                merge_listings(existing,occurrences.get(url,[doc])); additions.append(existing)
            continue
        try:
            LOG.info('Download %s',url)
            content=download_pdf(client,url)
        except Exception as exc:
            status['download_failures']+=1; status['failed_documents']+=1
            status['errors'].append(f'Download {url}: {type(exc).__name__}: {exc}')
            pending[url]={'document':doc,'error':str(exc),'last_attempt':stamp,'reprocess':force_parse}
            continue
        digest=content_hash(content)
        if digest in by_hash and (not force_parse or digest in processed_hashes):
            status['duplicate_count']+=1
            index[url]={'hash':digest,'checked_at':stamp}
            pending.pop(url,None)
            merge_listings(by_hash[digest],occurrences.get(url,[doc])); additions.append(by_hash[digest])
            continue
        try:
            with tempfile.TemporaryDirectory(prefix='dmc-') as directory:
                path=Path(directory)/'report.pdf'; path.write_bytes(content)
                text=extract_text(path)
            record=normalize(doc,text,digest,stamp)
            is_new=digest not in by_hash
            old_listings=by_hash.get(digest,{}).get('official',{}).get('listings',[])
            merge_listings(record,old_listings+occurrences.get(url,[doc]))
            processed_hashes.add(digest)
            additions.append(record); by_hash[digest]=record
            index[url]={'hash':digest,'checked_at':stamp}
            pending.pop(url,None)
            status['new_documents']+=int(is_new)
            status['reprocessed_documents']+=int(not is_new)
            if record['language']=='unknown': status['unknown_language_count']+=1
            if not text.strip(): status['no_text_count']+=1
        except Exception as exc:
            status['parsing_failures']+=1; status['failed_documents']+=1
            status['errors'].append(f'Parse {url}: {type(exc).__name__}: {exc}')
            pending[url]={'document':doc,'error':str(exc),'last_attempt':stamp,'reprocess':force_parse}
        time.sleep(pause)
    if owned_client: client.close()
    save_records(root,additions)
    write_json(root/'state/index.json',index)
    write_json(root/'state/pending.json',pending)
    status['pending_documents']=len(pending)
    # Preserve feeds exactly on total listing outage; partial runs merge only valid records.
    if category_success or additions:
        publish_feeds(root,list(by_hash.values()),now)
    if category_success==len(CATEGORIES) and status['failed_documents']==0 and not pending:
        status['last_successful_scrape']=stamp
        status['status']='success'
    elif category_success or additions:
        status['status']='partial'
    status['records_total']=len(by_hash)
    status['multilingual_documents_total']=sum(r['language']=='mul' for r in by_hash.values())
    status['unknown_language_total']=sum(r['language']=='unknown' for r in by_hash.values())
    status['extraction_incomplete_total']=sum(r['language']=='unknown' or r['extraction']['status']!='ok' for r in by_hash.values())
    write_json(root/'data/metadata.json',status)
    LOG.info('Run %s: checked=%d new=%d failed=%d duplicates=%d',status['status'],status['documents_checked'],status['new_documents'],status['failed_documents'],status['duplicate_count'])
    return status

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--max-pages',type=int,default=20)
    parser.add_argument('--bootstrap-days',type=int,default=7)
    parser.add_argument('--recheck',action='store_true',help='Re-download discovered known URLs to detect replacements')
    parser.add_argument('--reprocess',action='store_true',help='Re-extract discovered documents even when their content hash is known')
    args=parser.parse_args()
    if not 1<=args.max_pages<=500 or not 1<=args.bootstrap_days<=36500: parser.error('Invalid collection limits')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    try:
        status=run(args.root,max_pages=args.max_pages,bootstrap_days=args.bootstrap_days,recheck=args.recheck,reprocess=args.reprocess)
    except Exception as exc:
        previous=read_json(args.root/'data/metadata.json',{})
        previous.update(last_run=datetime.now(timezone.utc).isoformat(),status='error',errors=[f'Fatal pipeline failure: {type(exc).__name__}: {exc}'])
        write_json(args.root/'data/metadata.json',previous)
        LOG.exception('Fatal pipeline failure')
        return 1
    return 0 if status['status']=='success' else 1

if __name__=='__main__':
    raise SystemExit(main())
