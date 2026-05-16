import os
import time
import requests
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
from urllib.parse import urlencode, urlparse, urlunparse
from bs4 import BeautifulSoup

SCRAPER_API_KEY = os.environ['SCRAPER_API_KEY']

AFFILIATE_PARAMS = {
    'mkcid': '1',
    'mkrid': '711-53200-19255-0',
    'siteid': '0',
    'campid': '5338637261',
    'customid': '',
    'toolid': '10001',
    'mkevt': '1',
}

SEARCHES = [
    ('NES',          'NES game cartridge',       40),
    ('SNES',         'SNES game cartridge',       45),
    ('N64',          'Nintendo 64 game',          50),
    ('PS1',          'PS1 PlayStation game',      30),
    ('PS2',          'PS2 PlayStation 2 game',    25),
    ('Sega Genesis', 'Sega Genesis game',         30),
    ('Sega Saturn',  'Sega Saturn game',          50),
    ('Dreamcast',    'Sega Dreamcast game',       40),
    ('Game Boy',     'Game Boy game cartridge',   30),
    ('GBA',          'Game Boy Advance game',     35),
    ('Nintendo DS',  'Nintendo DS game',          20),
]


def scraper_get(url):
    api_url = f'http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={requests.utils.quote(url, safe="")}'
    return requests.get(api_url, timeout=60)


def make_affiliate_link(url):
    parsed = urlparse(url)
    clean = urlunparse(parsed._replace(query='', fragment=''))
    return clean + '?' + urlencode(AFFILIATE_PARAMS)


def scrape_ebay(keyword, max_price):
    params = urlencode({
        '_nkw': keyword,
        '_sop': '10',
        'LH_BIN': '1',
        '_udhi': str(max_price),
    })
    url = f'https://www.ebay.com/sch/i.html?{params}'

    try:
        resp = scraper_get(url)
        resp.raise_for_status()
    except Exception as e:
        print(f'  Error: {e}')
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    results = []

    for item in soup.select('li.s-item'):
        try:
            title_el = item.select_one('.s-item__title')
            price_el = item.select_one('.s-item__price')
            link_el  = item.select_one('a.s-item__link')
            cond_el  = item.select_one('.SECONDARY_INFO')

            if not (title_el and price_el and link_el):
                continue
            title = title_el.get_text(strip=True)
            if title.lower() == 'shop on ebay':
                continue

            price_text = price_el.get_text(strip=True).replace(',', '').split(' to ')[0]
            price = float(''.join(c for c in price_text if c.isdigit() or c == '.'))

            raw_url   = link_el['href'].split('?')[0]
            condition = cond_el.get_text(strip=True) if cond_el else 'Used'

            results.append({
                'title':     title[:100],
                'price':     price,
                'url':       make_affiliate_link(raw_url),
                'condition': condition,
            })
        except Exception:
            continue

    return results


def build_rss(all_deals):
    now      = datetime.now(timezone.utc)
    pub_date = now.strftime('%a, %d %b %Y %H:%M:%S +0000')

    rss     = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')
    SubElement(channel, 'title').text        = 'Retro Gaming eBay Deals'
    SubElement(channel, 'link').text         = 'https://www.ebay.com'
    SubElement(channel, 'description').text  = 'Daily retro gaming deals from eBay with affiliate links'
    SubElement(channel, 'language').text     = 'en-us'
    SubElement(channel, 'lastBuildDate').text = pub_date

    for label, items in all_deals.items():
        for deal in sorted(items, key=lambda x: x['price'])[:5]:
            el = SubElement(channel, 'item')
            SubElement(el, 'title').text       = f'[{label}] ${deal["price"]:.2f} — {deal["title"]}'
            SubElement(el, 'link').text        = deal['url']
            SubElement(el, 'guid', isPermaLink='true').text = deal['url']
            SubElement(el, 'pubDate').text     = pub_date
            SubElement(el, 'description').text = (
                f'<b>${deal["price"]:.2f}</b> | {deal["condition"]}<br/>'
                f'<a href="{deal["url"]}">{deal["title"]}</a>'
            )

    return parseString(tostring(rss, encoding='unicode')).toprettyxml(indent='  ')


def main():
    all_deals = {}
    for label, keyword, max_price in SEARCHES:
        print(f'Searching {label}...')
        items = scrape_ebay(keyword, max_price)
        print(f'  {len(items)} items found')
        if items:
            all_deals[label] = items
        time.sleep(1)

    xml = build_rss(all_deals)
    with open('feed.xml', 'w', encoding='utf-8') as f:
        f.write(xml)
    print(f'Done — {sum(len(v) for v in all_deals.values())} total deals written to feed.xml')


if __name__ == '__main__':
    main()
