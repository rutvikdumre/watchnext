import json, re, urllib.request, urllib.parse
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
      'Accept-Language': 'en-US,en;q=0.9', 'Accept': 'text/html,application/json'}
def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read().decode('utf-8', 'replace')
for q in ['inception', 'the dark knight', 'godfather part 2', 'interstelar', '3 idiots', 'amelie']:
    try:
        s, body = get('https://v3.sg.media-imdb.com/suggestion/x/%s.json?includeVideos=0' % urllib.parse.quote(q))
        d = json.loads(body).get('d', [])
        print('SUGG', q, s, [(x.get('id'), x.get('l'), x.get('y'), x.get('qid'), (x.get('i') or {}).get('imageUrl','')[-40:]) for x in d[:4]])
    except Exception as e:
        print('SUGG', q, 'ERR', repr(e))
print('RAW', body[:600])
for tid in ['tt1375666', 'tt0068646']:
    try:
        s, html = get('https://www.imdb.com/title/%s/' % tid)
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        print('TITLE', tid, s, len(html), 'ldjson' if m else 'NO-LD', html[:200].replace('\n',' ') if not m else '')
        if m:
            ld = json.loads(m.group(1)); print('LD keys', sorted(ld.keys())); print('LD', {k: ld.get(k) for k in ['name','genre','duration','datePublished','description','aggregateRating','image']})
            print('actors', [a.get('name') for a in ld.get('actor', [])][:5], 'director', ld.get('director'))
        nd = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
        print('NEXT_DATA', bool(nd))
    except Exception as e:
        print('TITLE', tid, 'ERR', repr(e))
try:
    import imdb; ia = imdb.IMDb(); r = ia.search_movie('Inception'); print('CINEMAGOER search', r[:3])
    m = ia.get_movie('1375666'); print('CINEMAGOER movie', m.get('title'), m.get('year'), m.get('genres'), bool(m.get('plot')), m.get('cover url'))
except Exception as e:
    print('CINEMAGOER ERR', repr(e)[:300])
