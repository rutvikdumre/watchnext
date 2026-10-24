import random

from django.contrib.auth import logout
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from lists.identity import my_lists

from . import imdb_api, wp_model
from .charts import TOP_CHARTS

GENRES = ['Action', 'Adventure', 'Biography', 'Comedy', 'Crime', 'Drama']
IMDB_DOWN = "Couldn't reach IMDb right now. Please try again in a moment."


def _chart(genre):
    return [{'title': m['name'], 'poster': imdb_api.poster(m['picurl'], 400), 'id': m['name']}
            for m in TOP_CHARTS[genre]]


def home(request):
    return render(request, 'main/home.html', {'genres': GENRES})


def index(request):
    return render(request, 'main/menu.html')


def topcharts(request, genre):
    if genre not in TOP_CHARTS:
        raise Http404
    return render(request, 'main/charts.html', {
        'heading': 'Top %s movies' % genre, 'movies': _chart(genre), 'genres': GENRES, 'active': genre,
    })


def surprise(request):
    genre = random.choice(GENRES)
    return render(request, 'main/charts.html', {
        'heading': 'Surprise genre: %s' % genre, 'movies': _chart(genre), 'genres': GENRES,
        'surprise': True,
    })


def searchByGenre(request, genre):
    titles = wp_model.titles_by_genre(genre, 12)
    if not titles:
        raise Http404
    found = imdb_api.posters_for(titles)
    movies = [{'title': t, 'poster': found[t][1], 'id': found[t][0] or t} for t in titles]
    return render(request, 'main/charts.html', {
        'heading': '%s picks from ranzol' % genre.title(), 'movies': movies, 'genres': GENRES,
    })


def genre(request):
    return redirect('/#genres')


def _search_page(request, mode):
    query = (request.GET.get('q') or request.POST.get('name') or '').strip()
    results, msg = [], ''
    if query:
        try:
            results = imdb_api.search(query, limit=12, known_titles=wp_model.known_titles())
            msg = '' if results else 'No movies found for "%s". Check the spelling or try another title.' % query
        except imdb_api.IMDbError:
            msg = IMDB_DOWN
    return render(request, 'main/search.html', {'mode': mode, 'q': query, 'results': results, 'msg': msg})


def search(request):
    """Recommendations: pick a movie you like."""
    return _search_page(request, 'suggest')


def searchDet(request):
    """Details: look up any movie."""
    return _search_page(request, 'detail')


def _resolve(name):
    """Turn an IMDb id or a movie name into an IMDb id (or None)."""
    if imdb_api.TITLE_ID.match(name):
        return name
    hit = imdb_api.best_match(name, known_titles=wp_model.known_titles())
    return hit['id'] if hit else None


def _movie_page(request, name, template, mode):
    try:
        tid = _resolve(name)
        if not tid:
            return render(request, 'main/search.html', {
                'mode': mode, 'q': name, 'results': [],
                'msg': 'No movies found for "%s". Check the spelling or try another title.' % name})
        if tid != name:
            return redirect('%s/%s' % ('/detail' if mode == 'detail' else '/suggestions', tid))
        movie = imdb_api.details(tid)
        picks = wp_model.recommend(movie)
    except imdb_api.IMDbError:
        return render(request, 'main/search.html', {'mode': mode, 'q': name, 'results': [], 'msg': IMDB_DOWN})
    lists = list(my_lists(request))
    on_lists = {wl.code for wl in lists if wl.items.filter(imdb_id=movie['id']).exists()}
    return render(request, template, {
        'movie': movie, 'picks': picks, 'similar': movie['similar'][:6],
        'my_lists': lists, 'on_lists': on_lists,
    })


def detail(request, id):
    return _movie_page(request, id, 'main/detail.html', 'detail')


def suggest(request, name):
    return _movie_page(request, name, 'main/suggest.html', 'suggest')


def api_suggest(request):
    """Autocomplete endpoint used by the search boxes."""
    query = (request.GET.get('q') or '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})
    try:
        results = imdb_api.search(query, limit=8, known_titles=wp_model.known_titles())
    except imdb_api.IMDbError:
        return JsonResponse({'results': [], 'error': IMDB_DOWN}, status=502)
    return JsonResponse({'results': results})


def logout_view(request):
    logout(request)
    return render(request, 'main/home.html', {'genres': GENRES, 'msg': 'You have been logged out.'})
