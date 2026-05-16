import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
from urllib.parse import urlencode, urlparse, urlunparse

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
    'User-Agent': 'RetroGameDealsFeed/1.0 (personal rss aggregator)',
}

MAX_AGE_DAYS = 30

RETRO_KEYWORDS = {
    'nes', 'snes', 'n64', 'nintendo 64', 'ps1', 'ps2', 'playstation 1',
    'playstation 2', 'sega genesis', 'mega drive', 'sega saturn', 'dreamcast',
    'game boy', 'gameboy', 'gba', 'game boy advance', 'nintendo ds', 'nds',
    '3ds', 'retro game', 'retro gaming', 'retro console', 'anbernic',
    'famicom', 'super famicom', 'atari', 'turbografx', 'neo geo',
    'super nintendo', 'virtual boy', 'game gear', 'lynx', 'jaguar',
}

# Subreddits + search queries — Reddit RSS needs no API key
RSS_SOURCES = [
    'https://www.reddit.com/r/gamecollecting/search.rss?q=ebay&sort=new&restrict_sr=1&limit=25',
    'https://www.reddit.com/r/gamedeals/search.rss?q=ebay+retro&sort=new&restrict_sr=1&limit=25',
    'https://www.reddit.com/r/retrogaming/search.rss?q=ebay+deal&sort=new&restrict_sr=1&limit=25',
    'https://www.reddit.com/r/gamecollecting/new.rss?limit=50',
    'https://www.reddit.com/r/gamedeals/new.rss?limit=50',
    'https://www.reddit.com/r/VideoGameDeals+GameDeals+gamecollecting/search.rss?q=ebay+retro&sort=new&limit=25',
]


def make_affiliate_link(url):
    parsed = urlparse(url)
    clean = urlunparse(parsed._replace(query='', fragment=''))
    return clean + '?' + urlencode(AFFILIATE_PARAMS)


def extract_ebay_item_url(text):
    """Pull first ebay.com/itm/ URL out of a block of text."""
    matches = re.findall(r'https?://(?:www\.)?ebay\.com/itm/[\w/-]+', text)
    return matches[0] if matches else None


def get_ebay_url_from_reddit_post(post_url):
    """Fetch Reddit post JSON and look for an eBay URL in title/selftext/url."""
    try:
        json_url = post_url.rstrip('/') + '.json'
        r = requests.get(json_url, headers=HEADERS, timeout=10)
        data = r.json()
        post = data[0]['data']['children'][0]['data']

        # Check the direct link first
        link_url = post.get('url', '')
        if 'ebay.com/itm/' in link_url:
            return link_url

        # Check selftext
        selftext = post.get('selftext', '')
        found = extract_ebay_item_url(selftext)
        if found:
            return found

        # Follow the link if it's not Reddit
        if link_url and 'reddit.com' not in link_url:
            try:
                r2 = requests.get(link_url, headers=HEADERS, timeout=8, allow_redirects=True)
                found = extract_ebay_item_url(r2.url + ' ' + r2.text[:3000])
                if found:
                    return found
            except Exception:
                pass
    except Exception as e:
        print(f'    Error: {e}')
    return None


def fetch_reddit_rss(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
    except Exception as e:
        print(f'  RSS error: {e}')
        return []

    NS = 'http://www.w3.org/2005/Atom'
    try:
        root = ET.fromstring(r.text)
    except Exception:
        return []

    results = []
    entries = root.findall(f'{{{NS}}}entry')

    for entry in entries:
        title_el   = entry.find(f'{{{NS}}}title')
        link_el    = entry.find(f'{{{NS}}}link')
        date_el    = entry.find(f'{{{NS}}}updated')
        if date_el is None:
            date_el = entry.find(f'{{{NS}}}published')
        content_el = entry.find(f'{{{NS}}}content')
        if content_el is None:
            content_el = entry.find(f'{{{NS}}}summary')

        if title_el is None:
            continue

        title   = (title_el.text or '').strip()
        link    = (link_el.get('href', '') if link_el is not None else '')
        pub     = (date_el.text or '').strip() if date_el is not None else ''
        content = (content_el.text or '') if content_el is not None else ''

        combined = (title + ' ' + content).lower()

        # must mention ebay
        if 'ebay' not in combined:
            continue

        # must be retro gaming
        if not any(kw in combined for kw in RETRO_KEYWORDS):
            continue

        # must be recent
        try:
            dt = datetime.fromisoformat(pub.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) - dt > timedelta(days=MAX_AGE_DAYS):
                continue
        except Exception:
            pass

        results.append({'title': title, 'link': link, 'pubDate': pub})

    return results


def build_rss(all_deals):
    now      = datetime.now(timezone.utc)
    pub_date = now.strftime('%a, %d %b %Y %H:%M:%S +0000')

    rss     = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')
    SubElement(channel, 'title').text        = 'Retro Gaming eBay Deals'
    SubElement(channel, 'link').text         = 'https://www.ebay.com'
    SubElement(channel, 'description').text  = 'Retro gaming eBay deals from Reddit with affiliate links'
    SubElement(channel, 'language').text     = 'en-us'
    SubElement(channel, 'lastBuildDate').text = pub_date

    seen = set()
    for deal in all_deals:
        url = deal.get('ebay_url') or deal['link']
        if url in seen:
            continue
        seen.add(url)

        el = SubElement(channel, 'item')
        SubElement(el, 'title').text       = deal['title']
        SubElement(el, 'link').text        = url
        SubElement(el, 'guid', isPermaLink='true').text = url
        SubElement(el, 'pubDate').text     = deal.get('pubDate', pub_date)
        SubElement(el, 'description').text = f'<a href="{url}">{deal["title"]}</a>'

    return parseString(tostring(rss, encoding='unicode')).toprettyxml(indent='  ')


def main():
    all_deals = []

    for rss_url in RSS_SOURCES:
        print(f'Fetching: {rss_url[:60]}...')
        deals = fetch_reddit_rss(rss_url)
        print(f'  {len(deals)} retro eBay posts found')

        for deal in deals:
            safe = deal["title"][:60].encode('ascii', 'replace').decode()
            print(f'  Getting eBay URL: {safe}')
            ebay_url = get_ebay_url_from_reddit_post(deal['link'])
            if ebay_url:
                deal['ebay_url'] = make_affiliate_link(ebay_url)
                print(f'    Got: {deal["ebay_url"][:80]}')
            else:
                deal['ebay_url'] = None
            all_deals.append(deal)
            time.sleep(1)

        time.sleep(2)

    xml = build_rss(all_deals)
    with open('feed.xml', 'w', encoding='utf-8') as f:
        f.write(xml)
    ebay_count = sum(1 for d in all_deals if d.get('ebay_url'))
    print(f'\nDone — {len(all_deals)} posts, {ebay_count} with eBay affiliate links')


if __name__ == '__main__':
    main()
