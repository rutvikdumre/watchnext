from unittest import mock

from django.contrib.auth.models import User
from django.test import Client, TestCase

from main import imdb_api
from main.tests import fake_request

from .models import Item, Member, Round, Ticket, Vote, WatchList

FETCH = {'HTTP_X_REQUESTED_WITH': 'fetch'}


@mock.patch('main.imdb_api._request', side_effect=fake_request)
class WatchlistFlowTests(TestCase):
    def setUp(self):
        imdb_api._suggest.cache_clear()
        imdb_api.details.cache_clear()
        self.alex = Client()   # guest who creates the list
        self.sam = Client()    # partner who joins with the invite link

    def make_list(self):
        resp = self.alex.post('/lists/new', {'name': 'Date night', 'your_name': 'Alex'})
        watchlist = WatchList.objects.get()
        self.assertRedirects(resp, '/lists/%s/?new=1' % watchlist.code, fetch_redirect_response=False)
        return watchlist

    def join(self, watchlist, client=None, name='Sam'):
        client = client or self.sam
        return client.post('/lists/join/%s' % watchlist.code, {'your_name': name})

    def test_guest_creates_list_and_partner_joins(self, _):
        wl = self.make_list()
        page = self.alex.get('/lists/%s/?new=1' % wl.code)
        self.assertContains(page, 'Now invite your partner or friends')
        self.assertContains(page, '/lists/join/%s' % wl.code)

        # Sam isn't a member yet: the list redirects to the invite page.
        self.assertRedirects(self.sam.get('/lists/%s/' % wl.code), '/lists/join/%s' % wl.code)
        self.assertContains(self.sam.get('/lists/join/%s' % wl.code), 'Date night')
        self.join(wl)
        self.assertEqual([m.name for m in wl.members.all()], ['Alex', 'Sam'])
        self.assertContains(self.sam.get('/lists/'), 'Date night')

    def test_add_vote_match_watch_flow(self, _):
        wl = self.make_list()
        self.join(wl)
        self.alex.post('/lists/%s/add' % wl.code, {'imdb_id': 'tt1375666'})
        item = Item.objects.get()
        self.assertEqual(item.title, 'Inception')
        self.assertEqual(item.added_by.name, 'Alex')
        # The person who adds a movie wants to watch it.
        self.assertEqual(Vote.objects.get().value, Vote.WANT)

        # Not a match until Sam also wants it.
        self.assertContains(self.alex.get('/lists/%s/?tab=matches' % wl.code), 'No matches yet')
        resp = self.sam.post('/lists/%s/items/%d/vote' % (wl.code, item.id), {'value': 'want'}, **FETCH)
        self.assertContains(resp, 'Everyone wants this')
        self.assertContains(self.alex.get('/lists/%s/?tab=matches' % wl.code), 'Inception')

        # Tapping the same vote again clears it.
        self.sam.post('/lists/%s/items/%d/vote' % (wl.code, item.id), {'value': 'want'}, **FETCH)
        self.assertEqual(item.votes.count(), 1)

        # Pick tonight's movie, then mark it watched.
        resp = self.alex.post('/lists/%s/pick' % wl.code)
        self.assertRedirects(resp, '/lists/%s/?pick=%d' % (wl.code, item.id), fetch_redirect_response=False)
        self.assertContains(self.alex.get(resp.url), "picked tonight")
        self.sam.post('/lists/%s/items/%d/watched' % (wl.code, item.id))
        self.assertContains(self.alex.get('/lists/%s/?tab=watched' % wl.code), 'Inception')

    def test_duplicate_add_is_ignored(self, _):
        wl = self.make_list()
        for _i in range(2):
            self.alex.post('/lists/%s/add' % wl.code, {'imdb_id': 'tt1375666'})
        self.assertEqual(wl.items.count(), 1)

    def test_strangers_cannot_change_a_list(self, _):
        wl = self.make_list()
        self.alex.post('/lists/%s/add' % wl.code, {'imdb_id': 'tt1375666'})
        item = Item.objects.get()
        stranger = Client()
        for url in ['/lists/%s/add' % wl.code, '/lists/%s/items/%d/vote' % (wl.code, item.id),
                    '/lists/%s/items/%d/remove' % (wl.code, item.id), '/lists/%s/pick' % wl.code]:
            with self.subTest(url=url):
                self.assertEqual(stranger.post(url, {'imdb_id': 'tt0816692', 'value': 'pass'}).status_code, 404)
        self.assertEqual(stranger.get('/lists/%s/state' % wl.code).status_code, 404)
        self.assertEqual(wl.items.count(), 1)

    def test_add_from_movie_page_for_logged_in_user(self, _):
        User.objects.create_user('neo', password='Xq9!zzLongPass')
        self.alex.login(username='neo', password='Xq9!zzLongPass')
        page = self.alex.get('/detail/tt1375666')
        self.assertContains(page, 'Start a shared watchlist')
        # Logged-in users don't need to type a name.
        self.alex.post('/lists/new', {'name': 'Our watchlist', 'imdb_id': 'tt1375666'})
        wl = WatchList.objects.get()
        self.assertEqual(wl.members.get().name, 'neo')
        self.assertEqual(wl.items.get().imdb_id, 'tt1375666')
        page = self.alex.get('/detail/tt1375666')
        self.assertContains(page, 'Already on')

    def test_live_update_version_changes(self, _):
        wl = self.make_list()
        before = self.alex.get('/lists/%s/state' % wl.code).json()['version']
        self.alex.post('/lists/%s/add' % wl.code, {'imdb_id': 'tt1375666'})
        after = self.alex.get('/lists/%s/state' % wl.code).json()['version']
        self.assertNotEqual(before, after)

    def test_last_member_leaving_deletes_list(self, _):
        wl = self.make_list()
        self.alex.post('/lists/%s/leave' % wl.code)
        self.assertFalse(WatchList.objects.exists())
        self.assertFalse(Member.objects.exists())

    def test_redirects_only_to_this_site(self, _):
        wl = self.make_list()
        resp = self.alex.post('/lists/%s/add' % wl.code, {'imdb_id': 'tt1375666', 'next': 'https://evil.example/'})
        self.assertEqual(resp.url, '/lists/%s/' % wl.code)


@mock.patch('main.imdb_api._request', side_effect=fake_request)
class MovieDrawTests(TestCase):
    def setUp(self):
        imdb_api._suggest.cache_clear()
        imdb_api.details.cache_clear()
        self.alex, self.sam = Client(), Client()
        self.alex.post('/lists/new', {'name': 'Us', 'your_name': 'Alex'})
        self.wl = WatchList.objects.get()
        self.sam.post('/lists/join/%s' % self.wl.code, {'your_name': 'Sam'})
        self.url = '/lists/%s/hat/' % self.wl.code

    def put(self, client, imdb_id):
        return client.post(self.url + 'pick', {'imdb_id': imdb_id})

    def test_full_draw(self, _):
        self.assertContains(self.alex.get(self.url), 'Start the draw')
        self.alex.post(self.url + 'start', {'picks_per_person': '2'})
        self.put(self.alex, 'tt1375666')
        self.put(self.alex, 'tt0071562')
        self.put(self.sam, 'tt1375666')  # same movie as Alex: two tickets
        page = self.alex.get(self.url)
        self.assertContains(page, '3</span> tickets in the hat')
        inception = page.context['movies'][0]
        self.assertEqual((inception['title'], inception['count'], inception['pct']), ('Inception', 2, 67))
        # The list page advertises the open draw.
        self.assertContains(self.sam.get('/lists/%s/' % self.wl.code), 'A movie draw is open')

        resp = self.sam.post(self.url + 'draw')
        self.assertRedirects(resp, self.url + '#reveal', fetch_redirect_response=False)
        rnd = Round.objects.get()
        self.assertIsNotNone(rnd.drawn_at)
        # The winner goes on the watchlist with a 👍 from everyone who picked it.
        item = self.wl.items.get(imdb_id=rnd.winner.imdb_id)
        pickers = set(rnd.tickets.filter(imdb_id=item.imdb_id).values_list('member__name', flat=True))
        self.assertEqual(set(item.votes.values_list('member__name', flat=True)), pickers)
        page = self.alex.get(self.url)
        self.assertContains(page, 'The hat has spoken')
        self.assertContains(page, 'Start another draw')
        # Drawing again does nothing once the hat is drawn.
        self.alex.post(self.url + 'draw')
        self.assertEqual(Round.objects.get().winner_id, rnd.winner_id)

    def test_pick_limits(self, _):
        self.alex.post(self.url + 'start', {'picks_per_person': '1'})
        self.put(self.alex, 'tt1375666')
        self.put(self.alex, 'tt1375666')  # duplicate from the same person
        self.put(self.alex, 'tt0071562')  # over the limit
        self.assertEqual(Ticket.objects.count(), 1)
        # Swap: remove and pick again.
        ticket = Ticket.objects.get()
        self.alex.post(self.url + 'unpick/%d' % ticket.id)
        self.put(self.alex, 'tt0071562')
        self.assertEqual(list(Ticket.objects.values_list('imdb_id', flat=True)), ['tt0071562'])
        # Sam can't remove Alex's pick.
        self.sam.post(self.url + 'unpick/%d' % Ticket.objects.get().id)
        self.assertEqual(Ticket.objects.count(), 1)

    def test_needs_two_movies(self, _):
        self.alex.post(self.url + 'start', {})
        self.put(self.alex, 'tt1375666')
        self.put(self.sam, 'tt1375666')
        self.alex.post(self.url + 'draw')
        self.assertIsNone(Round.objects.get().drawn_at)

    def test_secret_round_hides_other_picks(self, _):
        self.alex.post(self.url + 'start', {'secret': 'on'})
        self.put(self.alex, 'tt1375666')
        page = self.sam.get(self.url)
        self.assertContains(page, 'Picks are secret until the draw')
        self.assertNotContains(page, 'Inception')
        self.assertContains(self.alex.get(self.url), 'Inception')  # you see your own

    def test_two_tickets_mean_double_odds(self, _):
        self.alex.post(self.url + 'start', {})
        self.put(self.alex, 'tt1375666')
        self.put(self.sam, 'tt1375666')
        self.put(self.sam, 'tt0071562')
        rnd = Round.objects.get()
        tickets = list(rnd.tickets.all())
        wins = {'tt1375666': 0, 'tt0071562': 0}
        rng = __import__('random').Random(42)
        for _i in range(6000):
            wins[rng.choice(tickets).imdb_id] += 1
        self.assertAlmostEqual(wins['tt1375666'] / 6000, 2 / 3, delta=0.03)

    def test_strangers_cannot_use_the_hat(self, _):
        self.alex.post(self.url + 'start', {})
        stranger = Client()
        self.assertRedirects(stranger.get(self.url), '/lists/join/%s' % self.wl.code)
        for action in ['start', 'pick', 'draw']:
            self.assertEqual(stranger.post(self.url + action, {'imdb_id': 'tt1375666'}).status_code, 404)
