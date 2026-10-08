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
from build import build, ROUTES, URL, FULL_ADDRESS, ADDRESS, TEL, BUSINESS, page_groups

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
        self.in_title=False
        self.title=''
    def handle_starttag(self,tag,attributes):
        a=dict(attributes)
        if tag=='html': self.lang=a.get('lang')
        if a.get('id'): self.ids.add(a['id'])
        if tag=='h1': self.h1_count+=1
        if tag=='title': self.in_title=True
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
        if self.in_title:self.title+=data
    def handle_endtag(self,tag):
        if tag=='script':self.in_schema=False
        if tag=='title':self.in_title=False

def check_files(path,production):
    counts={'pages':0,'assets':0,'internal_links':0}
    documents={}
    titles=set()
    descriptions=set()
    entries=[(key,lang,route,routes) for key,routes in page_groups() for lang,route in routes.items()]
    for key,lang,route,routes in entries:
        content=(path/route.strip('/')/'index.html').read_text(encoding='utf-8')
        doc=Document();doc.feed(content)
        documents[route]=doc
        assert doc.lang==lang and doc.h1_count==1,(route,'language/H1')
        assert doc.canonical==[URL+route],(route,'canonical')
        assert doc.alternates=={**{code:URL+r for code,r in routes.items()},'x-default':URL+routes['ru']},(route,'hreflang')
        assert doc.metas['description'] and doc.title,(route,'metadata')
        assert doc.title not in titles and doc.metas['description'] not in descriptions,(route,'duplicate metadata')
        titles.add(doc.title);descriptions.add(doc.metas['description'])
        assert doc.metas['robots']==('index,follow' if production else 'noindex,nofollow')
        graph=json.loads(doc.schema)['@graph']
        expected={'WebSite','AutoRepair','WebPage'} | ({'Service','BreadcrumbList'} if key else set())
        assert {node['@type'] for node in graph}==expected
        repair=next(node for node in graph if node['@type']=='AutoRepair')
        assert repair['address']=={'@type':'PostalAddress',**ADDRESS}
        assert repair['telephone']==BUSINESS['telephone']
        assert 'aggregateRating' not in repair and 'review' not in repair
        assert len(repair['openingHoursSpecification'])==2
        if key:
            service=next(node for node in graph if node['@type']=='Service')
            assert service['url']==URL+route and service['provider']=={'@id':URL+'/#business'}
            assert 'offers' not in service
            crumbs=next(node for node in graph if node['@type']=='BreadcrumbList')['itemListElement']
            assert [item['position'] for item in crumbs]==[1,2]
            assert [item['item'] for item in crumbs]==[URL+ROUTES[lang],URL+route]
        assert FULL_ADDRESS in content
        assert '\ufffd' not in content and '????' not in content
        for asset in doc.assets:
            assert (path/asset.lstrip('/')).is_file(),(route,asset)
            counts['assets']+=1
        counts['pages']+=1
    for route,doc in documents.items():
        for link in doc.links:
            if link.startswith(('#','/')):
                parts=urlsplit(link)
                target=parts.path or route
                assert target in documents,(route,link)
                if parts.fragment: assert parts.fragment in documents[target].ids,(route,link)
            elif link.startswith(('tel:','sms:')):
                assert link.split(':',1)[1]==TEL
            elif link.startswith('https://www.google.com/maps/'):
                parts=urlsplit(link)
                query=parse_qs(parts.query)
                assert query['api']==['1']
                assert query.get('query',query.get('destination'))==[FULL_ADDRESS]
            else:raise AssertionError(('Unexpected link',link))
            counts['internal_links']+=1
    tree=ET.parse(path/'sitemap.xml')
    locations=[element.text for element in tree.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    assert len(locations)==len(set(locations)), 'duplicate sitemap URLs'
    assert set(locations)==(set(URL+r for r in documents) if production else set())
    if production:
        for item in tree.getroot():
            route=item.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text.removeprefix(URL)
            links={link.attrib['hreflang']:link.attrib['href'] for link in item.findall('{http://www.w3.org/1999/xhtml}link')}
            assert links==documents[route].alternates,(route,'sitemap alternatives')
    robots=(path/'robots.txt').read_text()
    assert ('Disallow: /' in robots)==(not production)
    return counts

def check_http(base_url, production):
    all_routes=[route for key,routes in page_groups() for route in routes.values()]
    for route in all_routes:
        with urlopen(base_url+route,timeout=5) as response:
            assert response.status==200
            content=response.read().decode('utf-8')
            assert '<h1>' in content and FULL_ADDRESS in content
            doc=Document();doc.feed(content)
            assert doc.metas['robots']==('index,follow' if production else 'noindex,nofollow')
    for route in ['/ua','/pl','/diagnostics','/pl/brakes']:
        with urlopen(base_url+route,timeout=5) as response:
            assert response.geturl().endswith(route+'/')
    for route in ['/missing-page/','/assets/','/pl/unknown-service/']:
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
    result={'status':'passed','current_mode':'production' if current_production else 'staging','current':current,'alternate_mode':alternate,'http':'15 pages, 4 redirects and 3 real 404s verified'}
    (root/'qa').mkdir(exist_ok=True)
    (root/'qa/verification-summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
