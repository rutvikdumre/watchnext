"""Who is the current visitor? A logged-in user or a guest with a cookie."""
import uuid

from django.db.models import Q

from .models import WatchList

COOKIE = 'wn_guest'
SALT = 'watchnext-guest'
ONE_YEAR = 60 * 60 * 24 * 365


def guest_token(request):
    return request.get_signed_cookie(COOKIE, default='', salt=SALT)


def get_or_make_guest_token(request):
    return guest_token(request) or uuid.uuid4().hex


def remember_guest(response, token):
    response.set_signed_cookie(COOKIE, token, salt=SALT, max_age=ONE_YEAR,
                               httponly=True, samesite='Lax', secure=False)
    return response


def member_for(request, watchlist):
    members = watchlist.members.all()
    if request.user.is_authenticated:
        mine = [m for m in members if m.user_id == request.user.id]
        if mine:
            return mine[0]
    token = guest_token(request)
    if token:
        mine = [m for m in members if m.guest_token == token]
        if mine:
            return mine[0]
    return None


def my_lists(request):
    who = Q(pk__in=[])
    if request.user.is_authenticated:
        who |= Q(members__user=request.user)
    token = guest_token(request)
    if token:
        who |= Q(members__guest_token=token)
    return WatchList.objects.filter(who).distinct().order_by('-updated_at')


def default_name(request):
    return request.user.username if request.user.is_authenticated else ''
