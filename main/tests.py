import json
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from . import imdb_api

IMG = 'https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@._V1_.jpg'

SUGGESTIONS = {
    'inception': [
        {'id': 'tt1375666', 'l': 'Inception', 'y': 2010, 'q': 'feature', 'qid': 'movie',
         's': 'Leonardo DiCaprio, Joseph Gordon-Levitt', 'i': {'imageUrl': IMG}},
        {'id': 'tt1790736', 'l': 'Inception: The Cobol Job', 'y': 2010, 'q': 'video', 'qid': 'video'},
        {'id': 'nm0000138', 'l': 'Leonardo DiCaprio', 's': 'Actor'},
    ],
    'interstelar': [
        {'id': 'tt4168808', 'l': 'Interstelar', 'y': 2014, 'q': 'feature', 'qid': 'movie', 'rank': 900000},
        {'id': 'tt0816692', 'l': 'Interstellar', 'y': 2014, 'q': 'feature', 'qid': 'movie', 'rank': 30},
    ],
    'the dark night': [
        {'id': 'tt0081120', 'l': 'Dark Night of the Scarecrow', 'y': 1981, 'q': 'TV movie', 'qid': 'tvMovie', 'rank': 50000},
        {'id': 'tt3576060', 'l': 'Dark Was the Night', 'y': 2014, 'q': 'feature', 'qid': 'movie', 'rank': 60000},
        {'id': 'tt7000000', 'l': 'Dark Was the Night', 'y': 2018, 'q': 'feature', 'qid': 'movie', 'rank': 70000},
    ],
    'the dark knight': [
        {'id': 'tt0468569', 'l': 'The Dark Knight', 'y': 2008, 'q': 'feature', 'qid': 'movie', 'rank': 40},
    ],
    'godfather part 2': [
        {'id': 'tt8756018', 'l': 'The Godfather: Part 2', 'y': 2018, 'q': 'TV series', 'qid': 'tvSeries'},
        {'id': 'tt0071562', 'l': 'The Godfather Part II', 'y': 1974, 'q': 'feature', 'qid': 'movie',
         'i': {'imageUrl': IMG}},
    ],
}


def fake_details(tid='tt1375666', title='Inception'):
    return {'data': {'title': {
        'id': tid, 'titleText': {'text': title}, 'releaseYear': {'year': 2010},
        'ratingsSummary': {'aggregateRating': 8.8, 'voteCount': 2700000},
        'runtime': {'seconds': 8880}, 'titleType': {'text': 'Movie'},
        'genres': {'genres': [{'text': 'Action'}, {'text': 'Sci-Fi'}]},
        'plot': {'plotText': {'plainText': 'A thief who steals corporate secrets.'}},
        'primaryImage': {'url': IMG},
        'principalCredits': [
            {'category': {'text': 'Director'}, 'credits': [{'name': {'nameText': {'text': 'Christopher Nolan'}}}]},
            {'category': {'text': 'Writer'}, 'credits': [{'name': {'nameText': {'text': 'Christopher Nolan'}}}]},
            {'category': {'text': 'Stars'}, 'credits': [{'name': {'nameText': {'text': 'Leonardo DiCaprio'}}}]},
        ],
        'spokenLanguages': {'spokenLanguages': [{'text': 'English'}]},
        'countriesOfOrigin': {'countries': [{'text': 'United States'}]},
        'moreLikeThisTitles': {'edges': [
            {'node': {'id': 'tt0816692', 'titleText': {'text': 'Interstellar'},
                      'releaseYear': {'year': 2014}, 'primaryImage': {'url': IMG}}},
        ]},
    }}}


def fake_request(url, data=None, headers=None):
    if data:  # GraphQL
        tid = json.loads(data)['variables']['id']
        titles = {i['id']: i['l'] for items in SUGGESTIONS.values() for i in items}
        return fake_details(tid, titles.get(tid, 'Inception'))
    query = url.split('/x/')[1].split('.json')[0].replace('%20', ' ')
    if query in SUGGESTIONS:
        return {'d': SUGGESTIONS[query]}
    # Anything else: pretend IMDb found a movie with that exact name.
    name = query.title()
    return {'d': [{'id': 'tt%07d' % (abs(hash(query)) % 10_000_000), 'l': name, 'y': 2000,
                   'q': 'feature', 'qid': 'movie', 'i': {'imageUrl': IMG}}]}


class PosterTests(TestCase):
    def test_upgrades_small_imdb_thumbnails(self):
        small = 'https://m.media-amazon.com/images/M/MV5Babc@._V1_SY150_CR0,0,101,150_.jpg%27%7D'
        self.assertEqual(imdb_api.poster(small, 500), 'https://m.media-amazon.com/images/M/MV5Babc@._V1_QL80_UX500_.jpg')

    def test_missing_poster_uses_default(self):
        self.assertEqual(imdb_api.poster(None), imdb_api.DEFAULT_POSTER)


@mock.patch('main.imdb_api._request', side_effect=fake_request)
class SearchTests(TestCase):
    def setUp(self):
        imdb_api._suggest.cache_clear()
        imdb_api.details.cache_clear()

    def test_search_filters_people_and_ranks_exact_movie_first(self, _):
        results = imdb_api.search('Inception')
        self.assertEqual([r['id'] for r in results], ['tt1375666', 'tt1790736'])

    def test_feature_films_rank_above_tv(self, _):
        results = imdb_api.search('godfather part 2')
        self.assertEqual(results[0]['id'], 'tt0071562')

    def test_popular_movie_beats_obscure_exact_typo_match(self, _):
        self.assertEqual(imdb_api.search('interstelar')[0]['title'], 'Interstellar')

    def test_close_spelling_of_known_movie(self, _):
        results = imdb_api.search('the dark night', known_titles=('The Dark Knight', 'Alien'))
        self.assertEqual(results[0]['title'], 'The Dark Knight')

    def test_details_parses_graphql(self, _):
        d = imdb_api.details('tt1375666')
        self.assertEqual(d['title'], 'Inception')
        self.assertEqual(d['runtime'], 148)
        self.assertEqual(d['directors'], ['Christopher Nolan'])
        self.assertEqual(d['similar'][0]['title'], 'Interstellar')
        self.assertIn('UX600', d['poster'])


@mock.patch('main.imdb_api._request', side_effect=fake_request)
class PageTests(TestCase):
    def setUp(self):
        imdb_api._suggest.cache_clear()
        imdb_api.details.cache_clear()

    def test_guest_can_use_everything(self, _):
        for url in ['/', '/index/', '/search/', '/suggest/', '/surprise', '/topcharts/Drama',
                    '/search/?q=inception', '/suggest/?q=inception', '/genres/Drama',
                    '/login/', '/register/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_home_offers_guest_mode(self, _):
        self.assertContains(self.client.get('/'), 'Continue as guest')

    def test_detail_page_shows_movie_and_recommendations(self, _):
        resp = self.client.get('/detail/tt1375666')
        self.assertContains(resp, 'Christopher Nolan')
        self.assertContains(resp, 'ranzol')
        self.assertContains(resp, 'Interstellar')
        self.assertEqual(len(resp.context['picks']), 6)

    def test_detail_by_name_redirects_to_imdb_id(self, _):
        resp = self.client.get('/detail/Inception')
        self.assertRedirects(resp, '/detail/tt1375666', fetch_redirect_response=False)

    def test_suggestions_page(self, _):
        resp = self.client.get('/suggestions/tt1375666')
        self.assertContains(resp, 'ranzol')

    def test_autocomplete_api(self, _):
        data = self.client.get('/api/suggest?q=inception').json()
        self.assertEqual(data['results'][0]['title'], 'Inception')
        self.assertEqual(self.client.get('/api/suggest?q=i').json(), {'results': []})

    def test_imdb_outage_shows_friendly_message(self, request_mock):
        request_mock.side_effect = imdb_api.IMDbError('down')
        resp = self.client.get('/detail/tt0000001')
        self.assertContains(resp, "Couldn&#x27;t reach IMDb")

    def test_signup_logs_user_in(self, _):
        resp = self.client.post('/register/', {
            'username': 'neo', 'email': 'neo@example.com',
            'password1': 'Xq9!zzLongPass', 'password2': 'Xq9!zzLongPass'})
        self.assertRedirects(resp, '/index/', fetch_redirect_response=False)
        self.assertContains(self.client.get('/index/'), 'Hi neo')
        self.assertTrue(User.objects.filter(username='neo').exists())
