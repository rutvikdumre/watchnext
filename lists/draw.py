"""Movie draw: everyone puts picks in the hat, then one ticket wins.

Every pick is one ticket, so a movie picked by two people has two tickets
and twice the chance of winning.
"""
import json
import random

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from main import imdb_api

from .models import Item, Round, Ticket, Vote
from .views import _list_and_member, _member_or_404


def _hat_url(code):
    return reverse('lists:hat', args=[code])


def _open_round(watchlist):
    return watchlist.rounds.filter(drawn_at__isnull=True).first()


def _group(tickets):
    """Group tickets by movie: [{imdb_id, title, poster, pickers, count, pct}]."""
    movies = {}
    for t in tickets:
        m = movies.setdefault(t.imdb_id, {'imdb_id': t.imdb_id, 'title': t.title, 'year': t.year,
                                          'poster': t.poster, 'pickers': [], 'tickets': []})
        m['pickers'].append(t.member)
        m['tickets'].append(t)
    total = len(tickets) or 1
    out = list(movies.values())
    for m in out:
        m['count'] = len(m['tickets'])
        m['pct'] = round(100 * m['count'] / total)
    out.sort(key=lambda m: (-m['count'], m['title']))
    return out


def hat(request, code):
    watchlist, me = _list_and_member(request, code)
    if not me:
        return redirect('lists:join', code)
    members = list(watchlist.members.all())
    current = _open_round(watchlist)
    latest_drawn = watchlist.rounds.filter(drawn_at__isnull=False).select_related('winner', 'drawn_by').first()

    ctx = {'watchlist': watchlist, 'me': me, 'members': members, 'tab': 'hat', 'round': current,
           'version': watchlist.updated_at.isoformat()}

    if current:
        tickets = list(current.tickets.select_related('member'))
        mine = [t for t in tickets if t.member_id == me.id]
        per_member = [{'member': m, 'count': sum(1 for t in tickets if t.member_id == m.id)} for m in members]
        ctx.update({
            'movies': _group(tickets),
            'my_picks': mine,
            'picks_left': max(current.picks_per_person - len(mine), 0),
            'per_member': per_member,
            'ticket_count': len(tickets),
            'hide_picks': current.secret,
        })
        picked_ids = {t.imdb_id for t in mine}
        ctx['from_list'] = [i for i in watchlist.items.filter(watched_at__isnull=True)
                            if i.imdb_id not in picked_ids][:12]

    if latest_drawn and latest_drawn.winner:
        tickets = list(latest_drawn.tickets.select_related('member'))
        ctx['last'] = latest_drawn
        ctx['last_movies'] = _group(tickets)
        ctx['last_winner_movie'] = next(m for m in ctx['last_movies'] if m['imdb_id'] == latest_drawn.winner.imdb_id)
        # Everything the reveal animation needs.
        ctx['reveal'] = json.dumps({
            'round': latest_drawn.id,
            'posters': [{'title': t.title, 'poster': t.poster, 'by': t.member.name} for t in tickets],
            'winner': next(i for i, t in enumerate(tickets) if t.id == latest_drawn.winner_id),
        })
    past = watchlist.rounds.filter(drawn_at__isnull=False, winner__isnull=False).select_related('winner', 'winner__member')
    # The latest result is shown big unless a new draw has started.
    ctx['history'] = list(past[:5] if current else past[1:6])
    ctx['invite_url'] = request.build_absolute_uri(reverse('lists:join', args=[code]))
    ctx['hat_count'] = len(current.tickets.all()) if current else 0
    if current:
        ctx['last'] = None
    return render(request, 'lists/hat.html', ctx)


@require_POST
def start(request, code):
    watchlist, me = _member_or_404(request, code)
    if not _open_round(watchlist):
        try:
            picks = min(max(int(request.POST.get('picks_per_person', 3)), 1), 10)
        except ValueError:
            picks = 3
        Round.objects.create(watchlist=watchlist, started_by=me, picks_per_person=picks,
                             secret=request.POST.get('secret') == 'on')
        watchlist.touch()
    return redirect(_hat_url(code))


@require_POST
def pick(request, code):
    watchlist, me = _member_or_404(request, code)
    current = _open_round(watchlist)
    if not current:
        messages.info(request, 'Start a new draw first.')
        return redirect(_hat_url(code))
    imdb_id = request.POST.get('imdb_id') or ''
    if not imdb_api.TITLE_ID.match(imdb_id):
        messages.error(request, 'That movie could not be found.')
        return redirect(_hat_url(code))
    mine = current.tickets.filter(member=me)
    if mine.filter(imdb_id=imdb_id).exists():
        messages.info(request, "That one's already in the hat from you.")
        return redirect(_hat_url(code))
    if mine.count() >= current.picks_per_person:
        messages.error(request, "You've used all %d picks. Remove one to swap it." % current.picks_per_person)
        return redirect(_hat_url(code))

    # Reuse what we already know about the movie, else ask IMDb.
    known = (watchlist.items.filter(imdb_id=imdb_id).first()
             or Ticket.objects.filter(round__watchlist=watchlist, imdb_id=imdb_id).first())
    if known:
        info = {'title': known.title, 'year': known.year, 'poster': known.poster}
    else:
        try:
            movie = imdb_api.details(imdb_id)
        except imdb_api.IMDbError:
            messages.error(request, "Couldn't reach IMDb right now. Please try again in a moment.")
            return redirect(_hat_url(code))
        info = {'title': movie['title'][:300], 'year': str(movie['year'] or ''),
                'poster': imdb_api.poster(movie['poster'], 400)}
    try:
        Ticket.objects.create(round=current, member=me, imdb_id=imdb_id, **info)
    except IntegrityError:
        pass
    watchlist.touch()
    others = current.tickets.filter(imdb_id=imdb_id).exclude(member=me).count()
    if others and not current.secret:
        messages.success(request, '%s is in the hat. Someone else picked it too, so it has %d tickets!' % (info['title'], others + 1))
    else:
        messages.success(request, '%s is in the hat 🎟️' % info['title'])
    return redirect(_hat_url(code))


@require_POST
def unpick(request, code, ticket_id):
    watchlist, me = _member_or_404(request, code)
    Ticket.objects.filter(pk=ticket_id, member=me, round__watchlist=watchlist, round__drawn_at__isnull=True).delete()
    watchlist.touch()
    return redirect(_hat_url(code))


@require_POST
def draw(request, code):
    watchlist, me = _member_or_404(request, code)
    current = _open_round(watchlist)
    if not current:
        return redirect(_hat_url(code))
    tickets = list(current.tickets.all())
    if len({t.imdb_id for t in tickets}) < 2:
        messages.error(request, 'Put at least two different movies in the hat first.')
        return redirect(_hat_url(code))
    winner = random.SystemRandom().choice(tickets)  # one ticket = one slot
    with transaction.atomic():
        won = Round.objects.filter(pk=current.pk, drawn_at__isnull=True).update(
            drawn_at=timezone.now(), drawn_by=me, winner=winner)
        if won:  # if two people tap Draw at once, only the first counts
            item, created = Item.objects.get_or_create(
                watchlist=watchlist, imdb_id=winner.imdb_id,
                defaults={'title': winner.title, 'year': winner.year, 'poster': winner.poster,
                          'added_by': winner.member})
            if item.watched_at:
                item.watched_at = None
                item.save(update_fields=['watched_at'])
            # Everyone who picked it wants to watch it.
            for t in tickets:
                if t.imdb_id == winner.imdb_id:
                    Vote.objects.update_or_create(item=item, member=t.member, defaults={'value': Vote.WANT})
    watchlist.touch()
    return redirect(_hat_url(code) + '#reveal')
