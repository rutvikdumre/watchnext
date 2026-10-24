import random

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from main import imdb_api

from . import identity
from .models import Item, Member, Vote, WatchList

TABS = ('towatch', 'matches', 'watched')


# ---------------------------------------------------------------- helpers

def _list_and_member(request, code):
    watchlist = get_object_or_404(WatchList.objects.prefetch_related('members'), code=code)
    return watchlist, identity.member_for(request, watchlist)


def _member_or_404(request, code):
    watchlist, member = _list_and_member(request, code)
    if not member:
        raise Http404
    return watchlist, member


def _safe_next(request, fallback):
    nxt = request.POST.get('next') or request.GET.get('next')
    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
        return nxt
    return fallback


def _is_fetch(request):
    return request.headers.get('X-Requested-With') == 'fetch'


def _decorate(items, members, me):
    """Attach vote info to each item for the templates."""
    member_count = len(members)
    for item in items:
        votes = list(item.votes.all())
        item.wants = [v.member for v in votes if v.value == Vote.WANT]
        item.passes = [v.member for v in votes if v.value == Vote.PASS]
        item.my_vote = next((v.value for v in votes if v.member_id == me.id), 0)
        item.score = len(item.wants) - len(item.passes)
        item.is_match = member_count > 1 and len(item.wants) == member_count
    return items


def _items(watchlist, me):
    items = list(watchlist.items.select_related('added_by').prefetch_related('votes__member'))
    return _decorate(items, list(watchlist.members.all()), me)


def _render_item(request, watchlist, me, item_id):
    item = next((i for i in _items(watchlist, me) if i.id == item_id), None)
    if item is None:
        return JsonResponse({'removed': True})
    return render(request, 'lists/_item.html', {'item': item, 'watchlist': watchlist, 'me': me,
                                                'members': list(watchlist.members.all())})


# ---------------------------------------------------------------- pages

def index(request):
    lists = list(identity.my_lists(request).prefetch_related('members', 'items'))
    for wl in lists:
        wl.to_watch = [i for i in wl.items.all() if not i.watched_at]
    return render(request, 'lists/index.html', {
        'lists': lists, 'default_name': identity.default_name(request),
    })


@require_POST
def create(request):
    name = (request.POST.get('name') or '').strip()[:80] or 'Our watchlist'
    your_name = (request.POST.get('your_name') or identity.default_name(request)).strip()[:40]
    if not your_name:
        messages.error(request, 'Tell us your name so your friends know who added what.')
        return redirect('lists:index')
    token = identity.get_or_make_guest_token(request)
    with transaction.atomic():
        watchlist = WatchList.objects.create(name=name)
        member = Member.objects.create(
            watchlist=watchlist, name=your_name, is_owner=True, guest_token=token,
            user=request.user if request.user.is_authenticated else None)
    imdb_id = request.POST.get('imdb_id')
    if imdb_id:
        _add_movie(request, watchlist, member, imdb_id)
    response = redirect(reverse('lists:detail', args=[watchlist.code]) + '?new=1')
    return identity.remember_guest(response, token)


def join(request, code):
    watchlist, member = _list_and_member(request, code)
    if member:
        return redirect('lists:detail', code)
    if request.method == 'POST':
        your_name = (request.POST.get('your_name') or '').strip()[:40]
        if not your_name:
            messages.error(request, 'Please enter your name.')
        else:
            token = identity.get_or_make_guest_token(request)
            Member.objects.create(watchlist=watchlist, name=your_name, guest_token=token,
                                  user=request.user if request.user.is_authenticated else None)
            watchlist.touch()
            messages.success(request, 'You joined “%s”. Add something you want to watch!' % watchlist.name)
            return identity.remember_guest(redirect('lists:detail', code), token)
    items = list(watchlist.items.filter(watched_at__isnull=True)[:6])
    return render(request, 'lists/join.html', {
        'watchlist': watchlist, 'members': list(watchlist.members.all()), 'preview': items,
        'count': watchlist.items.count(), 'default_name': identity.default_name(request),
    })


def detail(request, code):
    watchlist, me = _list_and_member(request, code)
    if not me:
        return redirect('lists:join', code)
    members = list(watchlist.members.all())
    items = _items(watchlist, me)
    tab = request.GET.get('tab') if request.GET.get('tab') in TABS else 'towatch'
    to_watch = sorted([i for i in items if not i.watched_at], key=lambda i: (-i.score, -i.added_at.timestamp()))
    matches = [i for i in to_watch if i.is_match]
    watched = sorted([i for i in items if i.watched_at], key=lambda i: i.watched_at, reverse=True)
    open_round = watchlist.rounds.filter(drawn_at__isnull=True).first()
    pick = None
    if request.GET.get('pick'):
        pick = next((i for i in to_watch if str(i.id) == request.GET['pick']), None)
    return render(request, 'lists/detail.html', {
        'watchlist': watchlist, 'me': me, 'members': members, 'tab': tab,
        'shown': {'towatch': to_watch, 'matches': matches, 'watched': watched}[tab],
        'counts': {'towatch': len(to_watch), 'matches': len(matches), 'watched': len(watched)},
        'invite_url': request.build_absolute_uri(reverse('lists:join', args=[code])),
        'is_new': request.GET.get('new') == '1', 'pick': pick,
        'open_round': open_round,
        'hat_count': open_round.tickets.count() if open_round else 0,
        'version': watchlist.updated_at.isoformat(),
    })


def state(request, code):
    """Tiny endpoint the list page polls to notice changes made by friends."""
    watchlist, _ = _member_or_404(request, code)
    return JsonResponse({'version': watchlist.updated_at.isoformat()})


# ---------------------------------------------------------------- actions

def _add_movie(request, watchlist, member, imdb_id):
    if not imdb_api.TITLE_ID.match(imdb_id or ''):
        messages.error(request, 'That movie could not be found.')
        return None
    existing = watchlist.items.filter(imdb_id=imdb_id).first()
    if existing:
        messages.info(request, '%s is already on “%s”.' % (existing.title, watchlist.name))
        return existing
    try:
        movie = imdb_api.details(imdb_id)
    except imdb_api.IMDbError:
        messages.error(request, "Couldn't reach IMDb right now. Please try again in a moment.")
        return None
    try:
        with transaction.atomic():
            item = Item.objects.create(
                watchlist=watchlist, imdb_id=imdb_id, title=movie['title'][:300],
                year=str(movie['year'] or ''), poster=imdb_api.poster(movie['poster'], 400), added_by=member)
            Vote.objects.create(item=item, member=member, value=Vote.WANT)
    except IntegrityError:  # someone added it at the same moment
        return watchlist.items.filter(imdb_id=imdb_id).first()
    watchlist.touch()
    messages.success(request, 'Added %s to “%s”.' % (item.title, watchlist.name))
    return item


@require_POST
def add(request, code):
    watchlist, me = _member_or_404(request, code)
    _add_movie(request, watchlist, me, request.POST.get('imdb_id'))
    return redirect(_safe_next(request, reverse('lists:detail', args=[code])))


@require_POST
def vote(request, code, item_id):
    watchlist, me = _member_or_404(request, code)
    item = get_object_or_404(Item, pk=item_id, watchlist=watchlist)
    value = Vote.WANT if request.POST.get('value') == 'want' else Vote.PASS
    current = Vote.objects.filter(item=item, member=me).first()
    if current and current.value == value:
        current.delete()  # tapping the same button again clears the vote
    elif current:
        current.value = value
        current.save(update_fields=['value'])
    else:
        Vote.objects.create(item=item, member=me, value=value)
    watchlist.touch()
    if _is_fetch(request):
        return _render_item(request, watchlist, me, item.id)
    return redirect(_safe_next(request, reverse('lists:detail', args=[code])) + '#item-%d' % item.id)


@require_POST
def watched(request, code, item_id):
    watchlist, me = _member_or_404(request, code)
    item = get_object_or_404(Item, pk=item_id, watchlist=watchlist)
    item.watched_at = None if item.watched_at else timezone.now()
    item.save(update_fields=['watched_at'])
    watchlist.touch()
    if _is_fetch(request):
        return JsonResponse({'removed': True})
    return redirect(_safe_next(request, reverse('lists:detail', args=[code])))


@require_POST
def remove(request, code, item_id):
    watchlist, me = _member_or_404(request, code)
    Item.objects.filter(pk=item_id, watchlist=watchlist).delete()
    watchlist.touch()
    if _is_fetch(request):
        return JsonResponse({'removed': True})
    return redirect(_safe_next(request, reverse('lists:detail', args=[code])))


@require_POST
def pick(request, code):
    """Pick tonight's movie: random choice among the most-wanted unwatched movies."""
    watchlist, me = _member_or_404(request, code)
    items = [i for i in _items(watchlist, me) if not i.watched_at and not i.passes]
    if not items:
        messages.info(request, 'Add a few movies (that nobody passed on) and ranzol will pick one.')
        return redirect('lists:detail', code)
    best = max(i.score for i in items)
    favourites = [i for i in items if i.score >= best - 1]
    choice = random.choice(favourites)
    return redirect(reverse('lists:detail', args=[code]) + '?pick=%d' % choice.id)


@require_POST
def leave(request, code):
    watchlist, me = _member_or_404(request, code)
    me.delete()
    if not Member.objects.filter(watchlist=watchlist).exists():
        watchlist.delete()
    else:
        watchlist.touch()
    messages.info(request, 'You left “%s”.' % watchlist.name)
    return redirect('lists:index')
