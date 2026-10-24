"""Small IMDb client.

Uses two public endpoints that IMDb's own website uses:
- the suggestion API (fast, typo-tolerant title search with posters)
- the GraphQL API (full title details and "more like this")

The old IMDbPY/cinemagoer scraper no longer works because IMDb blocks
scraping of its title pages.
"""
import difflib
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

SUGGEST_URL = 'https://v3.sg.media-imdb.com/suggestion/x/{}.json?includeVideos=0'
GRAPHQL_URL = 'https://caching.graphql.imdb.com/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/130.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}
TIMEOUT = 12
TITLE_KINDS = {'movie', 'tvMovie', 'tvSeries', 'tvMiniSeries', 'tvSpecial', 'video'}
DEFAULT_POSTER = '/static/default.png'
TITLE_ID = re.compile(r'^tt\d{5,10}$')


class IMDbError(Exception):
    pass


def poster(url, width=500):
    """Return a sharp, reasonably sized version of an IMDb image URL."""
    if not url:
        return DEFAULT_POSTER
    if 'media-amazon.com/images/' not in url or '._V1_' not in url:
        return url
    return url.split('._V1_')[0] + '._V1_QL80_UX%d_.jpg' % width


def normalize(text):
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode()
    text = text.lower().replace('&', ' and ')
    text = re.sub(r'[^a-z0-9 ]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _request(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={**HEADERS, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as exc:  # network errors, bad JSON, HTTP errors
        raise IMDbError(str(exc)) from exc


def _graphql(query, variables):
    body = json.dumps({'query': query, 'variables': variables}).encode()
    data = _request(GRAPHQL_URL, data=body, headers={
        'Content-Type': 'application/json',
        'x-imdb-client-name': 'imdb-web-next-localized',
        'x-imdb-user-country': 'US',
        'x-imdb-user-language': 'en-US',
    })
    if not data.get('data'):
        raise IMDbError(str(data.get('errors', 'empty GraphQL response'))[:300])
    return data['data']


# ---------------------------------------------------------------- search

@lru_cache(maxsize=2048)
def _suggest(query):
    q = normalize(query)
    if not q:
        return ()
    data = _request(SUGGEST_URL.format(urllib.parse.quote(q)))
    results = []
    for item in data.get('d', []):
        tid = item.get('id', '')
        if not TITLE_ID.match(tid) or item.get('qid') not in TITLE_KINDS:
            continue
        results.append({
            'id': tid,
            'title': item.get('l', ''),
            'year': item.get('y') or '',
            'kind': item.get('q', ''),
            'cast': item.get('s', ''),
            'poster': poster((item.get('i') or {}).get('imageUrl'), 300),
            'popularity': item.get('rank') or 10 ** 9,  # lower = more popular
        })
    return tuple(results)


_ROMAN = {'1': 'i', '2': 'ii', '3': 'iii', '4': 'iv', '5': 'v', '6': 'vi'}
_ROMAN_BACK = {v: k for k, v in _ROMAN.items()}


def _variants(query):
    """Alternative spellings to try when the plain query finds nothing."""
    q = normalize(query)
    words = q.split()
    out = []
    swapped = [_ROMAN.get(w, _ROMAN_BACK.get(w, w)) for w in words]
    if swapped != words:
        out.append(' '.join(swapped))
    if words and words[0] == 'the':
        out.append(' '.join(words[1:]))
    if len(words) > 2:
        out.append(' '.join(words[:-1]))
    return [v for v in out if v and v != q]


def _local_matches(query, titles, n=2):
    """Close spellings of titles we know, e.g. 'the dark night' -> 'The Dark Knight'."""
    q = normalize(query)
    by_norm = {normalize(t): t for t in titles}
    return [by_norm[m] for m in difflib.get_close_matches(q, list(by_norm), n=n, cutoff=0.8) if m != q]


def search(query, limit=8, known_titles=()):
    """Typo-tolerant title search. Returns a list of dicts."""
    query = (query or '').strip()
    if not query:
        return []
    seen, results = set(), []

    def add(items):
        for item in items:
            if item['id'] not in seen:
                seen.add(item['id'])
                results.append(item)

    add(_suggest(query))
    # Close spellings of well-known movies (typos IMDb's search misses).
    for alt in _local_matches(query, known_titles):
        try:
            add(_suggest(alt)[:1])
        except IMDbError:
            pass
    if len(results) < 3:
        for alt in _variants(query):
            try:
                add(_suggest(alt))
            except IMDbError:
                continue
            if len(results) >= limit:
                break

    # Rank by IMDb popularity, favouring exact title matches and feature films,
    # so 'interstelar' finds Interstellar before an obscure film called Interstelar.
    q = normalize(query)

    def score(item):
        s = item['popularity']
        if normalize(item['title']) == q:
            s /= 20
        if item['kind'] not in ('feature', 'TV movie'):
            s *= 5
        return s

    results.sort(key=score)
    return results[:limit]


def best_match(query, known_titles=(), year=None):
    results = search(query, limit=8, known_titles=known_titles)
    if year:
        same_year = [r for r in results if str(r['year']) == str(year)]
        if same_year:
            return same_year[0]
    return results[0] if results else None


def posters_for(titles, width=400, years=None):
    """Find posters for many titles in parallel. Returns {title: (id, poster)}."""
    years = years or {}

    def one(title):
        try:
            hit = best_match(title, year=years.get(title))
        except IMDbError:
            hit = None
        if not hit:
            return title, (None, DEFAULT_POSTER)
        return title, (hit['id'], poster(hit['poster'], width))

    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(pool.map(one, titles))


# ---------------------------------------------------------------- details

TITLE_QUERY = '''query($id: ID!) { title(id: $id) {
  id titleText { text } releaseYear { year } ratingsSummary { aggregateRating voteCount }
  runtime { seconds } genres { genres { text } } plot { plotText { plainText } }
  primaryImage { url } titleType { text }
  principalCredits { category { text } credits { name { nameText { text } } } }
  spokenLanguages { spokenLanguages { text } }
  countriesOfOrigin { countries { text } }
  moreLikeThisTitles(first: 12) { edges { node {
    id titleText { text } releaseYear { year } primaryImage { url }
  } } }
} }'''


@lru_cache(maxsize=512)
def details(title_id):
    """Full details for one IMDb title id (e.g. 'tt1375666')."""
    if not TITLE_ID.match(title_id or ''):
        raise IMDbError('bad title id')
    t = _graphql(TITLE_QUERY, {'id': title_id}).get('title')
    if not t:
        raise IMDbError('title not found')

    def text(obj, *keys):
        for k in keys:
            obj = (obj or {}).get(k)
        return obj

    credits = {}
    for group in t.get('principalCredits') or []:
        cat = text(group, 'category', 'text') or ''
        credits[cat.lower()] = [text(c, 'name', 'nameText', 'text') for c in group.get('credits') or []]

    seconds = text(t, 'runtime', 'seconds')
    similar = []
    for edge in text(t, 'moreLikeThisTitles', 'edges') or []:
        node = edge.get('node') or {}
        similar.append({
            'id': node.get('id'),
            'title': text(node, 'titleText', 'text'),
            'year': text(node, 'releaseYear', 'year') or '',
            'poster': poster(text(node, 'primaryImage', 'url'), 400),
        })

    return {
        'id': t.get('id', title_id),
        'title': text(t, 'titleText', 'text') or '',
        'year': text(t, 'releaseYear', 'year') or '',
        'kind': text(t, 'titleType', 'text') or '',
        'rating': text(t, 'ratingsSummary', 'aggregateRating'),
        'votes': text(t, 'ratingsSummary', 'voteCount'),
        'runtime': round(seconds / 60) if seconds else None,
        'genres': [g['text'] for g in text(t, 'genres', 'genres') or []],
        'plot': text(t, 'plot', 'plotText', 'plainText') or '',
        'poster': poster(text(t, 'primaryImage', 'url'), 600),
        'poster_full': poster(text(t, 'primaryImage', 'url'), 1000),
        'directors': credits.get('director') or credits.get('directors') or [],
        'writers': credits.get('writer') or credits.get('writers') or [],
        'cast': credits.get('stars') or credits.get('star') or [],
        'languages': [x['text'] for x in text(t, 'spokenLanguages', 'spokenLanguages') or []],
        'countries': [x['text'] for x in text(t, 'countriesOfOrigin', 'countries') or []],
        'similar': [s for s in similar if s['id'] and s['title']],
    }
