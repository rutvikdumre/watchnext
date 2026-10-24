import json, urllib.request
Q = '''query($id: ID!) { title(id: $id) {
  titleText { text } releaseYear { year } ratingsSummary { aggregateRating }
  runtime { seconds } genres { genres { text } } plot { plotText { plainText } }
  primaryImage { url width height }
  principalCredits { category { text } credits { name { nameText { text } } } }
  spokenLanguages { spokenLanguages { text } }
  countriesOfOrigin { countries { text } }
  moreLikeThisTitles(first: 8) { edges { node { id titleText { text } releaseYear { year } primaryImage { url } } } }
} }'''
for host in ['https://caching.graphql.imdb.com/', 'https://api.graphql.imdb.com/']:
    for tid in ['tt1375666', 'tt1187043']:
        body = json.dumps({'query': Q, 'variables': {'id': tid}}).encode()
        req = urllib.request.Request(host, data=body, headers={'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36',
            'x-imdb-client-name': 'imdb-web-next-localized', 'x-imdb-user-country': 'US', 'x-imdb-user-language': 'en-US'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                print('GQL', host, tid, r.status, r.read().decode()[:2500])
        except Exception as e:
            print('GQL', host, tid, 'ERR', repr(e), getattr(e, 'read', lambda: b'')()[:300])
# GraphQL title search
S = '''query($q: String!) { mainSearch(first: 6, options: {searchTerm: $q, type: TITLE, titleSearchOptions: {type: [MOVIE]}}) {
  edges { node { entity { ... on Title { id titleText { text } releaseYear { year } primaryImage { url } } } } } } }'''
body = json.dumps({'query': S, 'variables': {'q': 'dark knight'}}).encode()
req = urllib.request.Request('https://caching.graphql.imdb.com/', data=body, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=20) as r: print('SEARCH', r.status, r.read().decode()[:1200])
except Exception as e: print('SEARCH ERR', repr(e), getattr(e, 'read', lambda: b'')()[:500])
# poster resize check
for suf in ['._V1_SX600.jpg', '._V1_QL75_UX500_.jpg']:
    u = 'https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@' + suf
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20) as r:
            print('IMG', suf, r.status, r.headers.get('Content-Type'), len(r.read()))
    except Exception as e: print('IMG', suf, 'ERR', repr(e))
