#!/usr/bin/env python3
"""Verify generated SEO contracts and actual local HTTP responses."""
from html.parser import HTMLParser
from pathlib import Path
import argparse
import json
import tempfile
from urllib.request import urlopen
from urllib.error import HTTPError
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, parse_qs
from build import build, ROUTES, URL, FULL_ADDRESS, ADDRESS, TEL, BUSINESS

class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang=None
        self.metas={}
        self.canonical=[]
        self.alternates={}
        self.links=[]
        self.assets=[]
        self.ids=set()
        self.h1_count=0
        self.in_schema=False
        self.schema=''
    def handle_starttag(self,tag,attributes):
        a=dict(attributes)
        if tag=='html': self.lang=a.get('lang')
        if a.get('id'): self.ids.add(a['id'])
        if tag=='h1': self.h1_count+=1
        if tag=='meta': self.metas[a.get('name',a.get('property',''))]=a.get('content','')
        if tag=='link':
            if a.get('rel')=='canonical': self.canonical.append(a.get('href'))
            if a.get('rel')=='alternate': self.alternates[a.get('hreflang')]=a.get('href')
            if a.get('rel') in ['icon','stylesheet']: self.assets.append(a.get('href'))
        if tag=='a': self.links.append(a.get('href',''))
        if tag=='img': self.assets.append(a.get('src'))
        if tag=='script' and a.get('src'): self.assets.append(a['src'])
        if tag=='script' and a.get('type')=='application/ld+json': self.in_schema=True
    def handle_data(self,data):
        if self.in_schema:self.schema+=data
    def handle_endtag(self,tag):
        if tag=='script':self.in_schema=False

def check_files(path,production):
    counts={'pages':0,'assets':0,'internal_links':0}
    for lang,route in ROUTES.items():
        content=(path/route.strip('/')/'index.html').read_text(encoding='utf-8')
        doc=Document();doc.feed(content)
        assert doc.lang==lang and doc.h1_count==1,(route,'language/H1')
        assert doc.canonical==[URL+route],(route,'canonical')
        assert doc.alternates=={**{code:URL+r for code,r in ROUTES.items()},'x-default':URL+'/'},(route,'hreflang')
        assert doc.metas['description'] and ('<title>' in content),(route,'metadata')
        assert doc.metas['robots']==('index,follow' if production else 'noindex,nofollow')
        graph=json.loads(doc.schema)['@graph']
        assert {node['@type'] for node in graph}=={'WebSite','AutoRepair'}
        repair=next(node for node in graph if node['@type']=='AutoRepair')
        assert repair['address']=={'@type':'PostalAddress',**ADDRESS}
        assert repair['telephone']==BUSINESS['telephone']
        assert 'aggregateRating' not in repair and 'review' not in repair
        assert len(repair['openingHoursSpecification'])==2
        assert FULL_ADDRESS in content
        assert '\ufffd' not in content and '????' not in content
        for asset in doc.assets:
            assert (path/asset.lstrip('/')).is_file(),(route,asset)
            counts['assets']+=1
        for link in doc.links:
            if link.startswith('#'):assert link[1:] in doc.ids,(route,link)
            elif link.startswith('/'):
                assert (path/link.strip('/')/'index.html').is_file(),(route,link)
            elif link.startswith(('tel:','sms:')):
                assert link.split(':',1)[1]==TEL
            elif link.startswith('https://www.google.com/maps/'):
                parts=urlsplit(link)
                query=parse_qs(parts.query)
                assert query['api']==['1']
                assert query.get('query',query.get('destination'))==[FULL_ADDRESS]
            else:raise AssertionError(('Unexpected link',link))
            counts['internal_links']+=1
        counts['pages']+=1
    tree=ET.parse(path/'sitemap.xml')
    locations=[element.text for element in tree.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    assert set(locations)==(set(URL+r for r in ROUTES.values()) if production else set())
    robots=(path/'robots.txt').read_text()
    assert ('Disallow: /' in robots)==(not production)
    return counts

def check_http(base_url, production):
    for route in ROUTES.values():
        with urlopen(base_url+route,timeout=5) as response:
            assert response.status==200
            content=response.read().decode('utf-8')
            assert '<h1>' in content and FULL_ADDRESS in content
            doc=Document();doc.feed(content)
            assert doc.metas['robots']==('index,follow' if production else 'noindex,nofollow')
    for route in ['/ua','/pl']:
        with urlopen(base_url+route,timeout=5) as response:
            assert response.geturl().endswith(route+'/')
    for route in ['/missing-page/','/assets/']:
        try: urlopen(base_url+route,timeout=5)
        except HTTPError as response:
            assert response.code==404
            assert 'Страница не найдена' in response.read().decode('utf-8')
        else:raise AssertionError(('Expected 404',route))

if __name__=='__main__':
    root=Path(__file__).parent
    parser=argparse.ArgumentParser()
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    args=parser.parse_args()
    current_production=json.loads((root/'dist/build-info.json').read_text())['mode']=='production'
    current=check_files(root/'dist',current_production)
    with tempfile.TemporaryDirectory(prefix='avenor-alternate-mode-',dir='/tmp') as d:
        build(Path(d),not current_production)
        alternate=check_files(Path(d),not current_production)
    check_http(args.base_url.rstrip('/'),current_production)
    print(json.dumps({'status':'passed','current_mode':'production' if current_production else 'staging','current':current,'alternate_mode':alternate,'http':'3 pages, 2 redirects and 2 real 404s verified'},ensure_ascii=False,indent=2))
