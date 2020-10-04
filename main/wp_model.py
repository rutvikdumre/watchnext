
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import imdb
from csv import writer
import urllib.request
from PIL import Image

def append_list_as_row(file_name, list_of_elem):
    # Open file in append mode
    with open(file_name, 'a+', newline='') as write_obj:
        # Create a writer object from csv module
        csv_writer = writer(write_obj)
        # Add contents of list as last row in the csv file
        csv_writer.writerow(list_of_elem)
    write_obj.close()

def combine_features(row):
    return row['title']+" "+row['cast']+" "+row['director']+" "+row['writer']+" "+row['countries']+" "+row['language codes']+" "+str(row['runtime'])+" "+str(row['year'])+" "+str(row['rating'])+" "+str(row['genre'])+" "+str(row['index'])
def get_title_from_index(index):
    df = pd.read_csv('main/data_wp.csv')
    return df[df.index == index]["title"].values[0]
def get_index_from_title(title):
    df = pd.read_csv('main/data_wp.csv')
    return df[df.title == title]["index"].values[0]


def m_fit():
    df = pd.read_csv('main/data_wp.csv')
    features = ['title','cast','director','writer','countries','language codes','runtime','year','rating','genre','index']


    for feature in features:
        df[feature] = df[feature].fillna('') #filling all NaNs with blank string

    df["combined_features"] = df.apply(combine_features,axis=1) #applying combined_features() method over each rows of dataframe and storing the combined string in "combined_features" column

    #df.iloc[0].combined_features

    cv = CountVectorizer() #creating new CountVectorizer() object
    count_matrix = cv.fit_transform(df["combined_features"]) #feeding combined strings(movie contents) to CountVectorizer() object
    cosine_sim = cosine_similarity(count_matrix)
    return (df,cosine_sim)


def get_recommendation(name):
    df,cosine_sim=m_fit()
    ia = imdb.IMDb()
    movies = ia.search_movie(name)
    movie= movies[0]
    id1=movie.getID()
    #print(id1)

    ind=len(df)
    #print(ind)
    try:
      movie_user_likes = str(movie)
      movie_index = get_index_from_title(movie_user_likes)
      similar_movies = list(enumerate(cosine_sim[movie_index-1])) #accessing the row corresponding to given movie to find all the similarity scores for that movie and then enumerating over it
    except:
        movie = ia.get_movie(id1)
        #print(movie.get('title'))
        #try:
        ind+=1
        row_contents = [movie.get('title'), movie.get('cast')[0], movie.get('director')[0], movie.get('writer')[0], movie.get('countries')[0], movie.get('language codes')[0], movie.get('runtime')[0],movie.get('year'), movie.get('rating'),movie.get('genre')[0],ind]
        append_list_as_row('main/data_wp.csv', row_contents)
        df,cosine_sim=m_fit()
        movie_user_likes = str(movie)
        movie_index = get_index_from_title(movie_user_likes)
        similar_movies = list(enumerate(cosine_sim[movie_index-1])) #accessing the row corresponding to given movie to find all the similarity scores for that movie and then enumerating over it


    sorted_similar_movies = sorted(similar_movies,key=lambda x:x[1],reverse=True)[1:]

    i=0
    print("Top 6 similar movies to "+movie_user_likes+" are:\n")
    recommended_movies = []
    for element in sorted_similar_movies:
        recommended_movies.append(get_title_from_index(element[0]))
        i=i+1
        if i>5:
            break
    return recommended_movies

def removetag(s):
    alteredString = ""
    for i in range(len(s)):
        if s[i]+s[i+1]=='::':
            break
        alteredString+=s[i]
    return alteredString

def get_details(movie_name):
    ia = imdb.IMDb()
    filmID = ia.search_movie(movie_name)[0].movieID
    filmObj = ia.get_movie(filmID)
    filmCast = filmObj.get('cast')[0:5]
    cast = []
    for i in filmCast:
        cast.append(i['name'])
    filmGenres = filmObj.get('genres')
    filmTitle = filmObj.get('title')
    filmYear = filmObj.get('year')
    filmRating = filmObj.get('rating')
    filmDuration = filmObj.get('runtimes')[0]+ " minutes"
    plot = sorted(filmObj.get('plot'),key=len)[0:1]+sorted(filmObj.get('plot'),key=len)[-1:-2:-1]
    #print(plot)
    filmSummary = removetag(plot[1])
    filmPlot = removetag(plot[0])
    filmLangCodes = filmObj.get('language codes')[0].upper()
    filmPhotoUrl = filmObj.get('cover url')
    filmPhoto = Image.open(urllib.request.urlopen(filmPhotoUrl))
    return {'id':filmID,'title':filmTitle,'cast':cast,'image':filmPhoto,'picurl':filmPhotoUrl,'miniplot':filmPlot,'plot':filmSummary,'genres':filmGenres,'runtime':filmDuration,'year':filmYear,'rating':filmRating,'lang':filmLangCodes}
