import json, time, urllib.request
for base in ['https://watchnext.onrender.com']:
    for path in ['/', '/api/suggest?q=interstelar', '/detail/tt1375666']:
        for attempt in range(3):  # free plan may be asleep
            try:
                t = time.time()
                req = urllib.request.Request(base + path, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=90) as r:
                    body = r.read().decode('utf-8', 'replace')
                    print(base + path, r.status, '%.1fs' % (time.time() - t))
                    if path == '/':
                        print('  new build (guest button):', 'Continue as guest' in body, '| title:', body.split('<title>')[1].split('</title>')[0] if '<title>' in body else '?')
                    elif path.startswith('/api'):
                        print('  ', [(m['title'], m['year']) for m in json.loads(body)['results'][:3]])
                    else:
                        print('  has plot:', 'dream-sharing' in body, '| ranzol picks:', 'ranzol' in body, '| hi-res poster:', 'QL80_UX600' in body)
                break
            except Exception as e:
                print(base + path, 'ERR', repr(e)[:200]); time.sleep(10)
