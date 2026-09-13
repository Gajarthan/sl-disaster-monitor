"""Parse the official Joomla listings; structural failures are never empty feeds."""
from dataclasses import dataclass
from datetime import datetime
import re
from urllib.parse import urljoin, urlsplit, parse_qs, urlencode
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = 'https://www.dmc.gov.lk'
CATEGORIES = {'situation': (273, 1), 'weather': (274, 2), 'landslide': (276, 5), 'river_flood': (277, 6)}

class ListingError(ValueError):
    pass

def official_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in {'www.dmc.gov.lk', 'dmc.gov.lk'} or p.port not in (None,443) or p.username or p.password:
        raise ValueError('URL must use the official DMC HTTPS host')
    return url

def category_url(category, offset=0, limit=20):
    item, report_type = CATEGORIES[category]
    return BASE + '/index.php?' + urlencode(dict(option='com_dmcreports',view='reports',Itemid=item,report_type_id=report_type,lang='en',limit=limit,limitstart=offset))

def session():
    client = requests.Session()
    client.headers['User-Agent'] = 'SriLankaDisasterMonitor/1.0 (+https://github.com/Gajarthan/sl-disaster-monitor)'
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504], allowed_methods=['GET'], respect_retry_after_header=True)
    client.mount('https://', HTTPAdapter(max_retries=retry))
    return client

def get_response(client, url, **kwargs):
    # Validate each redirect before following it; no arbitrary remote fetches.
    for _ in range(5):
        official_url(url)
        response = client.get(url, timeout=(15,60), allow_redirects=False, **kwargs)
        if response.is_redirect:
            target = urljoin(url, response.headers['Location'])
            response.close()
            url = target
            continue
        response.raise_for_status()
        return response
    raise ValueError('Too many DMC redirects')

@dataclass
class ListingPage:
    documents: list
    next_offset: int | None

def parse_listing(html, source_page, category):
    soup = BeautifulSoup(html, 'html.parser')
    tables = [t for t in soup.select('table') if re.search(r'Time\s*\(24h\)', t.get_text(' ', strip=True))]
    if len(tables) != 1:
        raise ListingError('Expected exactly one report table with Title / Date / Time (24h) headers')
    documents = []
    for row in tables[0].find_all('tr')[1:]:
        cells = row.find_all('td', recursive=False)
        if len(cells) != 4:
            raise ListingError('Unexpected DMC row column count')
        title, date, time = [c.get_text(' ', strip=True) for c in cells[:3]]
        links = cells[3].select('a[href]')
        if not title or not links:
            raise ListingError('Missing report title or PDF link')
        try:
            datetime.strptime(date,'%Y-%m-%d')
            if time: datetime.strptime(time,'%H:%M')
            pdf = official_url(urljoin(source_page, links[0]['href']))
            if not urlsplit(pdf).path.lower().endswith('.pdf'):
                raise ValueError('Not a PDF URL')
        except ValueError as exc:
            raise ListingError(f'Invalid report row: {exc}') from exc
        documents.append(dict(title=title, description='', report_date=date, report_time=time,
                              document_type=category, source_page=source_page, source_pdf=pdf))
    if not documents:
        raise ListingError('Report table has no valid rows; source coverage cannot be verified')
    offset = int(parse_qs(urlsplit(source_page).query).get('limitstart',['0'])[0])
    offsets = []
    for link in soup.select('.pagination a[href]'):
        query = parse_qs(urlsplit(link['href']).query)
        value = query.get('limitstart',[''])[0]
        if value.isdigit() and int(value) > offset:
            offsets.append(int(value))
    return ListingPage(documents, min(offsets) if offsets else None)
