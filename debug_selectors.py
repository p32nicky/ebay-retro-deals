import requests
from urllib.parse import unquote

click_url = 'https://slickdeals.net/click?trd=Visit%20eBay&sdtid=19287414&tid=19287414&prop=diavail-false%7Cdincp-0%7Cdinpd-0%7Cdipgavail-false&pv=0694a298512c11f1a8546e6069f588e2&au=52a9c7114bab40d38a70e6a8116d0472'

r = requests.get(click_url, timeout=10, allow_redirects=True)
print('Final URL:', r.url)
print('Status:', r.status_code)
