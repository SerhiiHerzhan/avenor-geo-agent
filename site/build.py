#!/usr/bin/env python3
"""Build Avenor's static website. No third-party build dependencies."""
from pathlib import Path
from html import escape
import argparse
import json
import shutil

def write_text(path, content):
    """Standalone UTF-8 writer; the exported project needs only Python."""
    if '\ufffd' in content or '????' in content:
        raise ValueError('Invalid artifact encoding')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

def write_json(path, payload):
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2)+'\n')

ROOT = Path(__file__).resolve().parent
URL = 'https://stowarszawa.com'
PHONE = '+48 453 225 773'
TEL = '+48453225773'
ROUTES = {'ru': '/', 'uk': '/ua/', 'pl': '/pl/'}

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
    canonical = URL + route
    alternate = '\n'.join(f'<link rel="alternate" hreflang="{code}" href="{URL}{path}">' for code, path in ROUTES.items())
    nav = ''.join(f'<a href="#{x["id"]}">{e(x["label"])}</a>' for x in t['nav'])
    languages = ''.join(f'<a href="{path}" lang="{code}" hreflang="{code}" aria-label="{name}" {"aria-current=\"page\"" if code == lang else ""}>{label}</a>' for code,path,label,name in [('ru','/','RU','Русский'),('uk','/ua/','UA','Українська'),('pl','/pl/','PL','Polski')])
    cards = ''.join(f'<article class="service-card"><div class="service-card-top"><span class="number">{e(x["num"])}</span>{icon(x["icon"])}</div><h3>{e(x["title"])}</h3><p>{e(x["text"])}</p></article>' for x in t['services'])
    steps = ''.join(f'<li><span>{e(x["num"])}</span><div><h3>{e(x["title"])}</h3><p>{e(x["text"])}</p></div></li>' for x in t['steps'])
    points = ''.join(f'<li>{e(x)}</li>' for x in t['specialist_points'])
    faq = ''.join(f'<details><summary>{e(x["question"])}</summary><p>{e(x["answer"])}</p></details>' for x in t['faq'])
    hero = '<br>\n'.join(e(x) for x in t['hero_title'].split('\n'))
    robots = 'index,follow' if production else 'noindex,nofollow'
    # WebSite only: do not fabricate business address, ratings or offers.
    schema = json.dumps({'@context': 'https://schema.org', '@type': 'WebSite', '@id': URL+'/#website', 'url': URL+'/', 'name': 'Avenor Cars', 'inLanguage': ['ru','uk','pl']},ensure_ascii=False).replace('<','\\u003c')
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(t['title'])}</title>
<meta name="description" content="{e(t['description'])}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#f2e64b">
<link rel="canonical" href="{canonical}">
{alternate}
<link rel="alternate" hreflang="x-default" href="{URL}/">
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
</head>
<body>
<a class="skip-link" href="#main">{e(t['skip_link'])}</a>
<header class="site-header"><div class="container header-inner">
<a class="wordmark" href="{route}" aria-label="Avenor Cars"><span class="brand-symbol" aria-hidden="true">A<span></span></span><span>AVENOR<span class="wordmark-small">CARS · WARSAW</span></span></a>
<nav class="desktop-nav" aria-label="{e(t['menu_open'])}">{nav}</nav>
<div class="header-right"><div class="languages">{languages}</div><a class="header-phone" href="tel:{TEL}">{PHONE}</a><button type="button" class="menu-toggle" aria-expanded="false" aria-controls="mobile-nav" aria-label="{e(t['menu_open'])}" data-open="{e(t['menu_open'])}" data-close="{e(t['menu_close'])}"><span></span><span></span></button></div>
</div><nav id="mobile-nav" class="mobile-nav" hidden aria-label="{e(t['menu_open'])}">{nav}<a href="tel:{TEL}">{PHONE}</a></nav></header>
<main id="main">
<section class="hero"><div class="container hero-grid"><div class="hero-copy">
<p class="eyebrow"><span class="status-dot" aria-hidden="true"></span>{e(t['eyebrow'])}</p>
<h1>{hero}</h1><p class="hero-description">{e(t['hero_text'])}</p>
<div class="hero-actions"><a class="button button-yellow" href="tel:{TEL}">{e(t['call_cta'])}<span aria-hidden="true">↗</span></a><a class="text-link" href="#services">{e(t['services_cta'])}<span aria-hidden="true">↓</span></a></div>
<div class="hero-bottom"><span class="tiny-cross" aria-hidden="true">+</span><span>WARSZAWA · REMBERTÓW</span><span class="hero-line" aria-hidden="true"></span></div>
</div><div class="hero-art" aria-hidden="true"><span class="art-coordinate coordinate-top">AVENOR / CARS</span><div class="art-disc"></div><img src="/assets/car-blueprint.svg" alt="" width="920" height="620" fetchpriority="high"><span class="art-coordinate coordinate-bottom">52° N · 21° E <span>WARSAW</span></span></div></div></section>
<div class="facts-strip"><div class="container facts-grid"><div><span>{e(t['location_label'])}</span><strong>{e(t['location_value'])}</strong></div><div><span>{e(t['brands_label'])}</span><strong>{e(t['brands_value'])}</strong></div><div><span>{e(t['contact_label'])}</span><a href="tel:{TEL}">{PHONE}<span aria-hidden="true">↗</span></a></div></div></div>
<section id="services" class="section services-section"><div class="container"><div class="section-heading"><div><p class="kicker">01 / {e(t['intro_kicker'])}</p><h2>{e(t['intro_title'])}</h2></div><p class="heading-description">{e(t['intro_text'])}</p></div><div class="services-grid">{cards}</div><p class="price-note"><span aria-hidden="true">↗</span>{e(t['price_note'])}</p></div></section>
<section id="approach" class="approach-section"><div class="container approach-grid"><div><p class="kicker">02 / {e(t['approach_kicker'])}</p><h2>{e(t['approach_title'])}</h2><p class="approach-description">{e(t['approach_text'])}</p><a class="button button-dark" href="tel:{TEL}">{e(t['call_cta'])}<span aria-hidden="true">↗</span></a></div><ol class="steps">{steps}</ol></div></section>
<section class="specialist-section"><div class="container specialist-grid"><div><p class="kicker">03 / {e(t['specialist_kicker'])}</p><h2>{e(t['specialist_title'])}</h2></div><div><p>{e(t['specialist_text'])}</p><ul class="specialist-points">{points}</ul><div class="brand-list" aria-label="{e(t['brands_label'])}"><span>VAG</span><span>BMW</span><span>VOLVO</span><span>FORD</span></div></div></div></section>
<section id="faq" class="section faq-section"><div class="container faq-grid"><div><p class="kicker">04 / {e(t['faq_kicker'])}</p><h2>{e(t['faq_title'])}</h2></div><div class="faq-list">{faq}</div></div></section>
<section id="contacts" class="contact-section"><div class="container"><p class="kicker">05 / {e(t['contact_kicker'])}</p><div class="contact-grid"><div><h2>{e(t['contact_title'])}</h2><p>{e(t['contact_text'])}</p></div><div class="contact-details"><span class="phone-label">{e(t['phone_label'])}</span><a class="big-phone" href="tel:{TEL}">{PHONE}<span aria-hidden="true">↗</span></a><div class="contact-actions"><a class="button button-dark" href="tel:{TEL}">{e(t['call_cta'])}<span aria-hidden="true">↗</span></a><a class="sms-link" href="sms:{TEL}">{e(t['sms_cta'])}<span aria-hidden="true">↗</span></a></div><p class="contact-location"><strong>Warszawa, Rembertów</strong><br>{e(t['location_text'])}</p></div></div></div></section>
</main>
<footer class="site-footer"><div class="container footer-top"><a class="wordmark" href="{route}"><span class="brand-symbol" aria-hidden="true">A<span></span></span><span>AVENOR<span class="wordmark-small">CARS · WARSAW</span></span></a><p>{e(t['footer_text'])}</p><div class="languages">{languages}</div></div><div class="container footer-bottom"><span>© 2026 Avenor Cars</span><span>{e(t['footer_note'])}</span><a href="tel:{TEL}">{PHONE}</a></div></footer>
</body></html>'''.replace('↗', '<svg class="arrow-icon" aria-hidden="true" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 16 16 4M4 4h12v12"/></svg>')

def build(destination, production=False):
    data = json.loads((ROOT/'locales.json').read_text(encoding='utf-8'))
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT/'public', destination, dirs_exist_ok=True)
    for lang,path in ROUTES.items():
        target = destination / path.strip('/') / 'index.html'
        write_text(target, page(lang, data[lang], production))
    write_text(destination/'404.html', '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>Страница не найдена | Avenor Cars</title><link rel="stylesheet" href="/assets/site.css"></head><body class="not-found"><main><p class="kicker">404 / AVENOR CARS</p><h1>Страница не найдена</h1><p>Эта страница отсутствует. Перейдите на главную, чтобы найти услуги и контакты.</p><a class="button button-dark" href="/">На главную <span aria-hidden="true">↗</span></a></main></body></html>')
    robots = 'User-agent: *\nAllow: /\nSitemap: '+URL+'/sitemap.xml\n' if production else 'User-agent: *\nDisallow: /\n'
    write_text(destination/'robots.txt',robots)
    items = []
    for lang,path in ROUTES.items():
        alternates=''.join(f'<xhtml:link rel="alternate" hreflang="{code}" href="{URL}{r}"/>' for code,r in ROUTES.items())
        alternates+=f'<xhtml:link rel="alternate" hreflang="x-default" href="{URL}/"/>'
        items.append(f'<url><loc>{URL}{path}</loc>{alternates}</url>')
    write_text(destination/'sitemap.xml','<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'+''.join(items)+'</urlset>\n' if production else '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>\n')
    write_json(destination/'build-info.json',{'mode': 'production' if production else 'staging', 'routes': list(ROUTES.values()), 'source': 'Avenor Cars draft brief', 'unverified_business_facts': True})
    print(f'Built {len(ROUTES)} localized pages: {destination} ({"production" if production else "staging"})')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--production',action='store_true',help='Enable indexing. Use only after business facts and domain are confirmed.')
    parser.add_argument('--out',type=Path,default=ROOT/'dist')
    args=parser.parse_args()
    build(args.out.resolve(),args.production)
