"""ranzol: content-based movie recommender.

Builds a bag-of-words vector for every movie in data_wp.csv (cast, director,
writer, country, language, runtime, year, rating, genre) and recommends the
movies with the highest cosine similarity. Movies that are not in the CSV are
vectorised on the fly from their IMDb details.
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import imdb_api

DATA_FILE = Path(__file__).resolve().parent / 'data_wp.csv'
FEATURES = ['title', 'cast', 'director', 'writer', 'countries', 'language codes',
            'runtime', 'year', 'rating', 'genre']
LANG_CODES = {'English': 'en', 'Hindi': 'hi', 'French': 'fr', 'Japanese': 'ja', 'Italian': 'it',
              'German': 'de', 'Spanish': 'es', 'Korean': 'ko', 'Swedish': 'sv', 'Russian': 'ru',
              'Portuguese': 'pt', 'Chinese': 'zh', 'Mandarin': 'zh', 'Tamil': 'ta', 'Telugu': 'te',
              'Persian': 'fa', 'Turkish': 'tr', 'Danish': 'da', 'Arabic': 'ar'}


def _combine(row):
    return ' '.join(str(row[f]) for f in FEATURES)


@lru_cache(maxsize=1)
def model():
    df = pd.read_csv(DATA_FILE)
    df = df.drop_duplicates(subset='title').reset_index(drop=True)
    for f in FEATURES:
        df[f] = df[f].fillna('')
    vectorizer = CountVectorizer()
    matrix = vectorizer.fit_transform(df.apply(_combine, axis=1))
    df['norm'] = df['title'].map(imdb_api.normalize)
    return df, vectorizer, matrix


def known_titles():
    return tuple(model()[0]['title'])


def _year(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def titles_by_genre(genre, n=12):
    df = model()[0]
    return list(df[df.genre.str.lower() == genre.lower()]['title'][:n])


def _row_from_details(d):
    """Turn IMDb details into the same feature string the CSV rows use."""
    lang = d['languages'][0] if d['languages'] else ''
    row = {
        'title': d['title'],
        'cast': d['cast'][0] if d['cast'] else '',
        'director': d['directors'][0] if d['directors'] else '',
        'writer': d['writers'][0] if d['writers'] else '',
        'countries': d['countries'][0] if d['countries'] else '',
        'language codes': LANG_CODES.get(lang, lang),
        'runtime': d['runtime'] or '',
        'year': d['year'],
        'rating': d['rating'] or '',
        'genre': d['genres'][0] if d['genres'] else '',
    }
    return _combine(row)


def recommend(d, n=6):
    """Return up to n [title, poster, imdb_id] lists similar to the movie `d`.

    `d` is a details dict from imdb_api.details().
    """
    df, vectorizer, matrix = model()
    norm = imdb_api.normalize(d['title'])
    matches = df.index[df['norm'] == norm].tolist()
    if matches:
        vector = matrix[matches[0]]
    else:
        vector = vectorizer.transform([_row_from_details(d)])
    scores = cosine_similarity(vector, matrix)[0]
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    rows = [i for i in ranked if df.at[i, 'norm'] != norm][:n]
    titles = [df.at[i, 'title'] for i in rows]
    found = imdb_api.posters_for(titles, years={df.at[i, 'title']: _year(df.at[i, 'year']) for i in rows})
    return [[t, found[t][1], found[t][0]] for t in titles]
