import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

AFFILIATE_PARAMS = {
    'mkcid': '1',
    'mkrid': '711-53200-19255-0',
    'siteid': '0',
    'campid': '5338637261',
    'customid': '',
    'toolid': '10001',
    'mkevt': '1',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36',
}

SEARCHES = [
    'retro game ebay',
    'NES game ebay',
    'SNES game ebay',
    'Nintendo 64 ebay',
    'PS1 PlayStation ebay',
    'PS2 PlayStation ebay',
    'Sega Genesis ebay',
    'Dreamcast ebay',
    'Game Boy ebay',
    'Game Boy Advance ebay',
    'Nintendo DS ebay',
]


def make_affiliate_link(ebay_url):
    parsed = urlparse(ebay_url)
    clean = urlunparse(parsed._replace(query='', fragment=''))
    return clean + '?' + urlencode(AFFILIATE_PARAMS)


def get_ebay_url_from_slickdeals(deal_url):
    """Fetch Slickdeals deal page, find click URL, follow redirect to eBay."""
    try:
        r = requests.get(deal_url, headers=HEADERS, timeout=10)
        click_urls = re.findall(r'https://slickdeals\.net/click\?[^"\'<\s]+', r.text)
        if not click_urls:
            return None

        click_url = click_urls[0].replace('&amp;', '&')
        redirect = requests.get(click_url, headers=HEADERS, timeout=10, allow_redirects=False)
        location = redirect.headers.get('Location', '')

        if 'ebay.com/itm/' in location:
            return make_affiliate_link(location)
    except Exception as e:
        print(f'    Error: {e}')
    return None


def fetch_slickdeals(query):
    url = f'https://slickdeals.net/newsearch.php?q={requests.utils.quote(query)}&searcharea=deals&searchin=first_word&rss=1'
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f'  RSS fetch error: {e}')
        return []

    root = ET.fromstring(r.text)
    results = []

    for item in root.findall('.//item'):
        title = item.findtext('title', '').strip()
        link  = item.findtext('link', '').strip()
        desc  = item.findtext('description', '')
        pub   = item.findtext('pubDate', '')

        if 'ebay' not in title.lower() and 'ebay' not in desc.lower():
            continue

        results.append({
            'title':   title,
            'link':    link,
            'pubDate': pub,
        })

    return results


def build_rss(all_deals):
    now      = datetime.now(timezone.utc)
    pub_date = now.strftime('%a, %d %b %Y %H:%M:%S +0000')

    rss     = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')
    SubElement(channel, 'title').text        = 'Retro Gaming eBay Deals'
    SubElement(channel, 'link').text         = 'https://www.ebay.com'
    SubElement(channel, 'description').text  = 'Daily retro gaming eBay deals via Slickdeals with affiliate links'
    SubElement(channel, 'language').text     = 'en-us'
    SubElement(channel, 'lastBuildDate').text = pub_date

    seen = set()
    for deal in all_deals:
        url = deal.get('ebay_url') or deal['link']
        if url in seen:
            continue
        seen.add(url)

        el = SubElement(channel, 'item')
        SubElement(el, 'title').text        = deal['title']
        SubElement(el, 'link').text         = url
        SubElement(el, 'guid', isPermaLink='true').text = url
        SubElement(el, 'pubDate').text      = deal.get('pubDate', pub_date)
        SubElement(el, 'description').text  = (
            f'<a href="{url}">{deal["title"]}</a>'
        )

    return parseString(tostring(rss, encoding='unicode')).toprettyxml(indent='  ')


def main():
    all_deals = []

    for query in SEARCHES:
        print(f'Searching: {query}')
        deals = fetch_slickdeals(query)
        print(f'  {len(deals)} eBay deals found')

        for deal in deals:
            print(f'  Getting eBay URL: {deal["title"][:60]}')
            ebay_url = get_ebay_url_from_slickdeals(deal['link'])
            deal['ebay_url'] = ebay_url
            if ebay_url:
                print(f'    Got: {ebay_url[:80]}')
            all_deals.append(deal)
            time.sleep(1)

        time.sleep(2)

    xml = build_rss(all_deals)
    with open('feed.xml', 'w', encoding='utf-8') as f:
        f.write(xml)
    print(f'\nDone — {len(all_deals)} deals written to feed.xml')


if __name__ == '__main__':
    main()
