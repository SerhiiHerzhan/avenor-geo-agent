#!/usr/bin/env python3
"""Build Avenor's static website. No third-party build dependencies."""
from pathlib import Path
from html import escape
import argparse
import json
import shutil
from urllib.parse import urlencode

def write_text(path, content):
    """Standalone UTF-8 writer; the exported project needs only Python."""
    if '\ufffd' in content or '????' in content:
        raise ValueError('Invalid artifact encoding')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

def write_json(path, payload):
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2)+'\n')

ROOT = Path(__file__).resolve().parent
BUSINESS = json.loads((ROOT/'business.json').read_text(encoding='utf-8'))
URL = BUSINESS['url']
PHONE = BUSINESS['telephone']
TEL = PHONE.replace(' ', '')
ADDRESS = BUSINESS['address']
FULL_ADDRESS = f"{ADDRESS['streetAddress']}, {ADDRESS['postalCode']} {ADDRESS['addressLocality']}"
MAPS_URL = 'https://www.google.com/maps/search/?' + urlencode({'api':'1','query':FULL_ADDRESS})
DIRECTIONS_URL = 'https://www.google.com/maps/dir/?' + urlencode({'api':'1','destination':FULL_ADDRESS})
ROUTES = {'ru': '/', 'uk': '/ua/', 'pl': '/pl/'}
SERVICE_KEYS = ('diagnostics', 'oil-change', 'suspension', 'brakes')

def routes_for(service=None):
    return {lang: home + (service + '/' if service else '') for lang, home in ROUTES.items()}

def page_groups():
    return [(None, ROUTES)] + [(key, routes_for(key)) for key in SERVICE_KEYS]

def language_links(lang, routes):
    return ''.join(f'<a href="{routes[code]}" lang="{code}" hreflang="{code}" aria-label="{name}" {"aria-current=\"page\"" if code == lang else ""}>{label}</a>' for code,label,name in [('ru','RU','Русский'),('uk','UA','Українська'),('pl','PL','Polski')])

def schema_graph():
    return [
        {'@type':'WebSite','@id':URL+'/#website','url':URL+'/','name':BUSINESS['name'],'inLanguage':['ru','uk','pl'],'publisher':{'@id':URL+'/#business'}},
        {'@type':'AutoRepair','@id':URL+'/#business','url':URL+'/','name':BUSINESS['name'],'logo':URL+'/assets/avenor-logo.webp','telephone':PHONE,'address':{'@type':'PostalAddress',**ADDRESS},'hasMap':MAPS_URL,'openingHoursSpecification':[{'@type':'OpeningHoursSpecification',**row} for row in BUSINESS['openingHoursSpecification']]}
    ]

def head(lang, t, production, routes, extra_nodes=None):
    e = escape
    canonical = URL + routes[lang]
    graph = schema_graph() + [{'@type':'WebPage','@id':canonical+'#page','url':canonical,'name':t['title'],'inLanguage':lang,'isPartOf':{'@id':URL+'/#website'},'about':{'@id':URL+'/#business'}}] + (extra_nodes or [])
    schema = json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('<','\\u003c')
    alternates = '\n'.join(f'<link rel="alternate" hreflang="{code}" href="{URL}{path}">' for code,path in routes.items())
    robots = 'index,follow' if production else 'noindex,nofollow'
    return f'''<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(t['title'])}</title>
<meta name="description" content="{e(t['description'])}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#f2e64b">
<link rel="canonical" href="{canonical}">
{alternates}
<link rel="alternate" hreflang="x-default" href="{URL}{routes['ru']}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Avenor Cars">
<meta property="og:title" content="{e(t['title'])}">
<meta property="og:description" content="{e(t['description'])}">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="{t['locale']}">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/site.css">
<script src="/assets/site.js" defer></script>
<script type="application/ld+json">{schema}</script>
</head>'''

ICONS = {
    'scan': '<rect x="4" y="3" width="16" height="12" rx="2"/><path d="M8 21h8M12 15v6M7 9h2l2-3 2 6 2-3h2"/>',
    'oil': '<path d="M5 7h9v12H4V9l1-2ZM7 7V4h5v3M14 10l4-3 3 4-4 3M9 11v4"/>',
    'wheel': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="m12 3 0 6m0 6v6M3 12h6m6 0h6M6 6l4 4m4 4 4 4M6 18l4-4m4-4 4-4"/>',
    'brake': '<circle cx="11" cy="12" r="8"/><circle cx="11" cy="12" r="2"/><path d="M16 5h5v14h-5M8 6v2m-3 4h2m1 6v-2"/>',
}

def icon(name):
    return '<svg class="service-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">' + ICONS[name] + '</svg>'

def page(lang, t, production):
    e = escape
    route = ROUTES[lang]
    nav = ''.join(f'<a href="#{x["id"]}">{e(x["label"])}</a>' for x in t['nav'])
    languages = language_links(lang, ROUTES)
    details = {'ru':'Подробнее об услуге','uk':'Докладніше про послугу','pl':'Więcej o usłudze'}[lang]
    cards = ''.join(f'<article class="service-card"><div class="service-card-top"><span class="number">{e(x["num"])}</span>{icon(x["icon"])}</div><h3><a href="{routes_for(key)[lang]}">{e(x["title"])}</a></h3><p>{e(x["text"])}</p><a class="service-detail-link" href="{routes_for(key)[lang]}">{details}<span aria-hidden="true">↗</span></a></article>' for key,x in zip(SERVICE_KEYS,t['services']))
    steps = ''.join(f'<li><span>{e(x["num"])}</span><div><h3>{e(x["title"])}</h3><p>{e(x["text"])}</p></div></li>' for x in t['steps'])
    points = ''.join(f'<li>{e(x)}</li>' for x in t['specialist_points'])
    faq = ''.join(f'<details><summary>{e(x["question"])}</summary><p>{e(x["answer"])}</p></details>' for x in t['faq'])
    price_rows = ''.join(f'<tr><th scope="row">{e(x["name"])}</th><td class="price-amount">{e(x["amount"])}</td><td>{e(x["note"])}</td></tr>' for x in t['prices'])
    hours = ''.join(f'<div><dt>{e(x["days"])}</dt><dd>{e(x["time"])}</dd></div>' for x in t['hours'])
    hero = '<br>\n'.join(e(x) for x in t['hero_title'].split('\n'))
    return f'''<!doctype html>
<html lang="{lang}">
{head(lang, t, production, ROUTES)}
<body>
<a class="skip-link" href="#main">{e(t['skip_link'])}</a>
<header class="site-header"><div class="container header-inner">
<a class="wordmark" href="{route}" aria-label="Avenor Cars"><img class="brand-logo" src="/assets/avenor-logo.webp" alt="Avenor Cars" width="480" height="320" decoding="async"></a>
<nav class="desktop-nav" aria-label="{e(t['menu_open'])}">{nav}</nav>
<div class="header-right"><div class="languages">{languages}</div><a class="header-phone" href="tel:{TEL}">{PHONE}</a><button type="button" class="menu-toggle" aria-expanded="false" aria-controls="mobile-nav" aria-label="{e(t['menu_open'])}" data-open="{e(t['menu_open'])}" data-close="{e(t['menu_close'])}"><span></span><span></span></button></div>
</div><nav id="mobile-nav" class="mobile-nav" hidden aria-label="{e(t['menu_open'])}">{nav}<a href="tel:{TEL}">{PHONE}</a></nav></header>
<main id="main">
<section class="hero"><picture class="hero-background" aria-hidden="true"><img src="/assets/workshop-hero.webp" srcset="/assets/workshop-hero-960.webp 960w, /assets/workshop-hero.webp 1536w" sizes="100vw" alt="" width="1536" height="1024" fetchpriority="high" decoding="async"></picture><div class="container hero-grid"><div class="hero-copy">
<p class="eyebrow"><span class="status-dot" aria-hidden="true"></span>{e(t['eyebrow'])}</p>
<h1>{hero}</h1><p class="hero-description">{e(t['hero_text'])}</p>
<div class="hero-actions"><a class="button button-yellow" href="tel:{TEL}">{e(t['call_cta'])}<span aria-hidden="true">↗</span></a><a class="text-link" href="#services">{e(t['services_cta'])}<span aria-hidden="true">↓</span></a></div>
<div class="hero-bottom"><span class="tiny-cross" aria-hidden="true">+</span><span>WARSZAWA · {e(BUSINESS['display_area'].upper())}</span><span class="hero-line" aria-hidden="true"></span></div>
</div></div></section>
<div class="facts-strip"><div class="container facts-grid"><div><span>{e(t['location_label'])}</span><strong>{e(t['location_value'])}</strong></div><div><span>{e(t['brands_label'])}</span><strong>{e(t['brands_value'])}</strong></div><div><span>{e(t['contact_label'])}</span><a href="tel:{TEL}">{PHONE}<span aria-hidden="true">↗</span></a></div></div></div>
<section id="services" class="section services-section"><div class="container"><div class="section-heading"><div><p class="kicker">01 / {e(t['intro_kicker'])}</p><h2>{e(t['intro_title'])}</h2></div><p class="heading-description">{e(t['intro_text'])}</p></div><div class="services-grid">{cards}</div><p class="price-note"><span aria-hidden="true">↗</span>{e(t['price_note'])}</p></div></section>
<section id="prices" class="section prices-section"><div class="container"><div class="section-heading"><div><p class="kicker">{e(t['prices_kicker'])}</p><h2>{e(t['prices_title'])}</h2></div><p class="heading-description">{e(t['prices_intro'])}</p></div><div class="price-table-wrap"><table class="price-table"><caption class="visually-hidden">{e(t['prices_title'])}</caption><thead><tr>{''.join(f'<th scope="col">{e(label)}</th>' for label in t['prices_columns'])}</tr></thead><tbody>{price_rows}</tbody></table></div><p class="price-note">{e(t['prices_note'])}</p><div class="warranty-note"><h3>{e(t['warranty_title'])}</h3><p>{e(t['warranty_text'])}</p></div></div></section>
<section id="approach" class="approach-section"><div class="container approach-grid"><div><p class="kicker">02 / {e(t['approach_kicker'])}</p><h2>{e(t['approach_title'])}</h2><p class="approach-description">{e(t['approach_text'])}</p><a class="button button-dark" href="tel:{TEL}">{e(t['call_cta'])}<span aria-hidden="true">↗</span></a></div><ol class="steps">{steps}</ol></div></section>
<section class="specialist-section"><div class="container specialist-grid"><div><p class="kicker">03 / {e(t['specialist_kicker'])}</p><h2>{e(t['specialist_title'])}</h2></div><div><p>{e(t['specialist_text'])}</p><ul class="specialist-points">{points}</ul><div class="brand-list" aria-label="{e(t['brands_label'])}"><span>VAG</span><span>BMW</span><span>VOLVO</span><span>FORD</span></div></div></div></section>
<section id="faq" class="section faq-section"><div class="container faq-grid"><div><p class="kicker">04 / {e(t['faq_kicker'])}</p><h2>{e(t['faq_title'])}</h2></div><div class="faq-list">{faq}</div></div></section>
<section id="contacts" class="contact-section"><div class="container"><p class="kicker">05 / {e(t['contact_kicker'])}</p><div class="contact-grid"><div><h2>{e(t['contact_title'])}</h2><p>{e(t['contact_text'])}</p><div class="contact-address"><span class="phone-label">{e(t['address_label'])}</span><a href="{e(MAPS_URL)}" target="_blank" rel="noopener noreferrer">{e(FULL_ADDRESS)}</a></div><div class="opening-hours"><span class="phone-label">{e(t['hours_label'])}</span><dl>{hours}</dl></div><a class="sms-link route-link" href="{e(DIRECTIONS_URL)}" target="_blank" rel="noopener noreferrer">{e(t['route_cta'])}<span aria-hidden="true">↗</span></a></div><div class="contact-details"><span class="phone-label">{e(t['phone_label'])}</span><a class="big-phone" href="tel:{TEL}">{PHONE}<span aria-hidden="true">↗</span></a><div class="contact-actions"><a class="button button-dark" href="tel:{TEL}">{e(t['call_cta'])}<span aria-hidden="true">↗</span></a><a class="sms-link" href="sms:{TEL}">{e(t['sms_cta'])}<span aria-hidden="true">↗</span></a></div><p class="contact-location">{e(t['location_text'])}</p></div></div></div></section>
</main>
<footer class="site-footer"><div class="container footer-top"><a class="wordmark" href="{route}"><img class="brand-logo" src="/assets/avenor-logo.webp" alt="Avenor Cars" width="480" height="320" loading="lazy" decoding="async"></a><p>{e(t['footer_text'])}</p><div class="languages">{languages}</div></div><div class="container footer-bottom"><span>© 2026 Avenor Cars</span><span>{e(t['footer_note'])}</span><a href="tel:{TEL}">{PHONE}</a></div></footer>
</body></html>'''.replace('↗', '<svg class="arrow-icon" aria-hidden="true" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 16 16 4M4 4h12v12"/></svg>')

def service_page(lang, main_text, data, key, production):
    """Reuse the shared header, contact area and footer from the home template."""
    e = escape
    labels = data['labels']
    t = data['services'][key]
    routes = routes_for(key)
    canonical = URL + routes[lang]
    shell = page(lang, main_text, production)
    header = shell[shell.index('<header '):shell.index('</header>') + len('</header>')]
    footer = shell[shell.index('<footer '):shell.index('</footer>') + len('</footer>')]
    contact = shell[shell.index('<section id="contacts"'):shell.index('</main>')]
    old_languages = language_links(lang, ROUTES)
    languages = language_links(lang, routes)
    header = header.replace(old_languages, languages)
    footer = footer.replace(old_languages, languages)
    for item in main_text['nav']:
        header = header.replace(f'href="#{item["id"]}"', f'href="{ROUTES[lang]}#{item["id"]}"')
    nodes = [
        {'@type':'Service','@id':canonical+'#service','url':canonical,'name':t['h1'],'serviceType':t['h1'],'description':t['description'],'provider':{'@id':URL+'/#business'},'areaServed':{'@type':'City','name':'Warszawa'}},
        {'@type':'BreadcrumbList','@id':canonical+'#breadcrumbs','itemListElement':[
            {'@type':'ListItem','position':1,'name':labels['home'],'item':URL+ROUTES[lang]},
            {'@type':'ListItem','position':2,'name':t['h1'],'item':canonical}
        ]}
    ]
    sections = ''.join('<section class="service-content-section" id="'+e(section['id'])+'"><h2>'+e(section['heading'])+'</h2>'+''.join('<p>'+e(p)+'</p>' for p in section.get('paragraphs',[]))+('<ul>'+''.join('<li>'+e(item)+'</li>' for item in section['bullets'])+'</ul>' if section.get('bullets') else '')+'</section>' for section in t['sections'])
    toc = ''.join(f'<li><a href="#{e(section["id"])}">{e(section["heading"])}</a></li>' for section in t['sections'])
    toc += f'<li><a href="#service-faq">{e(labels["faq"])}</a></li><li><a href="#booking">{e(labels["booking"])}</a></li>'
    faq = ''.join(f'<details><summary>{e(item["question"])}</summary><p>{e(item["answer"])}</p></details>' for item in t['faq'])
    related = ''.join(f'<a class="related-card" href="{routes_for(other)[lang]}"><span>{e(data["services"][other]["h1"])}</span><span aria-hidden="true">↗</span></a>' for other in SERVICE_KEYS if other != key)
    meta = {**t, 'locale':main_text['locale']}
    return f'''<!doctype html>
<html lang="{lang}">
{head(lang, meta, production, routes, nodes)}
<body class="service-page">
<a class="skip-link" href="#main">{e(main_text['skip_link'])}</a>
{header}
<main id="main">
<section class="service-hero"><div class="container">
<nav class="breadcrumbs" aria-label="{e(labels['home'])}"><ol><li><a href="{ROUTES[lang]}">{e(labels['home'])}</a></li><li aria-current="page">{e(t['h1'])}</li></ol></nav>
<p class="kicker">AVENOR CARS / WARSZAWA</p>
<h1>{e(t['h1'])}</h1><p class="service-lead">{e(t['intro'])}</p>
<div class="service-hero-actions"><a class="button button-yellow" href="tel:{TEL}">{e(labels['call'])}<span aria-hidden="true">↗</span></a><a class="text-link" href="#booking">{e(labels['booking'])}<span aria-hidden="true">↓</span></a></div>
<p class="service-location">{e(FULL_ADDRESS)} · VAG · BMW · Volvo · Ford</p>
</div></section>
<div class="container service-layout"><aside class="service-toc"><nav aria-label="{e(labels['on_this_page'])}"><p class="kicker">{e(labels['on_this_page'])}</p><ul>{toc}</ul></nav><a class="service-back" href="{ROUTES[lang]}#services">← {e(labels['back'])}</a></aside>
<div class="service-content">{sections}
<section class="service-content-section" id="service-faq"><h2>{e(labels['faq'])}</h2><div class="faq-list">{faq}</div></section>
<section class="service-booking" id="booking"><p class="kicker">{e(labels['price'])}</p><h2>{e(labels['booking'])}</h2><p class="service-price">{e(t['price'])}</p><p>{e(t['booking_text'])}</p><div class="contact-actions"><a class="button button-dark" href="tel:{TEL}">{e(labels['call'])}<span aria-hidden="true">↗</span></a><a class="sms-link" href="sms:{TEL}">{e(labels['sms'])}<span aria-hidden="true">↗</span></a></div></section>
<section class="service-content-section"><h2>{e(labels['related'])}</h2><div class="related-services">{related}</div></section>
</div></div>
{contact}
</main>
{footer}
</body></html>'''.replace('↗', '<svg class="arrow-icon" aria-hidden="true" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 16 16 4M4 4h12v12"/></svg>')

def build(destination, production=True):
    data = json.loads((ROOT/'locales.json').read_text(encoding='utf-8'))
    services = json.loads((ROOT/'services.json').read_text(encoding='utf-8'))
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT/'public', destination, dirs_exist_ok=True)
    for lang,path in ROUTES.items():
        target = destination / path.strip('/') / 'index.html'
        write_text(target, page(lang, data[lang], production))
        for key in SERVICE_KEYS:
            write_text(destination/routes_for(key)[lang].strip('/')/'index.html', service_page(lang, data[lang], services[lang], key, production))
    write_text(destination/'404.html', '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>Страница не найдена | Avenor Cars</title><link rel="stylesheet" href="/assets/site.css"></head><body class="not-found"><main><p class="kicker">404 / AVENOR CARS</p><h1>Страница не найдена</h1><p>Эта страница отсутствует. Перейдите на главную, чтобы найти услуги и контакты.</p><a class="button button-dark" href="/">На главную <span aria-hidden="true">↗</span></a></main></body></html>')
    robots = 'User-agent: *\nAllow: /\nSitemap: '+URL+'/sitemap.xml\n' if production else 'User-agent: *\nDisallow: /\n'
    write_text(destination/'robots.txt',robots)
    items = []
    for key,routes in page_groups():
        for lang,path in routes.items():
            alternates=''.join(f'<xhtml:link rel="alternate" hreflang="{code}" href="{URL}{r}"/>' for code,r in routes.items())
            alternates+=f'<xhtml:link rel="alternate" hreflang="x-default" href="{URL}{routes["ru"]}"/>'
            items.append(f'<url><loc>{URL}{path}</loc>{alternates}</url>')
    write_text(destination/'sitemap.xml','<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'+''.join(items)+'</urlset>\n' if production else '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>\n')
    all_routes = [route for key,routes in page_groups() for route in routes.values()]
    write_json(destination/'build-info.json',{'mode':'production' if production else 'staging','routes':all_routes,'business_data_source':BUSINESS['data_source'],'indexing_authorized_by_owner':BUSINESS['indexing_authorized']})
    print(f'Built {len(all_routes)} localized pages: {destination} ({"production" if production else "staging"})')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--production',dest='production',action='store_true',help='Build the owner-authorized indexable release (default).')
    modes.add_argument('--staging',dest='production',action='store_false',help='Build a non-indexable development preview.')
    parser.set_defaults(production=True)
    parser.add_argument('--out',type=Path,default=ROOT/'dist')
    args=parser.parse_args()
    build(args.out.resolve(),args.production)
