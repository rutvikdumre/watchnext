import time
from main import imdb_api, wp_model
kt = wp_model.known_titles()
for q in ['inception', 'interstelar', 'godfather part 2', 'the dark night', 'shawshank redemtion', 'amelie', '3 idiots', 'lord of the rings two towers', 'spirited away', 'parasite', 'xqzvj', 'the kid', 'pulp fction', 'avengers endgame', 'dangal', 'the prestige']:
    t = time.time(); r = imdb_api.search(q, known_titles=kt)
    print('SEARCH %-30r %.2fs ->' % (q, time.time() - t), [(x['title'], x['year'], x['kind']) for x in r[:3]])
for tid in ['tt1375666']:
    t = time.time(); d = imdb_api.details(tid)
    print('DETAIL', d['title'], d['year'], d['rating'], d['runtime'], d['genres'], d['directors'], d['cast'][:2], d['poster'][-30:], len(d['similar']))
    p = wp_model.recommend(d); print('  RANZOL %.2fs' % (time.time() - t), [(x[0], x[2], x[1][-25:]) for x in p])
import urllib.request
u = imdb_api.details('tt1375666')['poster']
print('POSTER GET', urllib.request.urlopen(urllib.request.Request(u, headers=imdb_api.HEADERS), timeout=20).status, u)
