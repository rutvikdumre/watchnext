# views.py
import imdb
import random
from django.contrib.auth import logout
from django.shortcuts import render,redirect
from django.http import HttpResponse, HttpResponseRedirect
from .models import MoviesToWatch, Movie
from  .wp_model import get_recommendation, get_details, searchMovie, genreSearch
# Create your views here.
global topchart
topchart={'Adventure':[{'name': 'Interstellar', 'picurl': 'https://m.media-amazon.com/images/M/MV5BZjdkOTU3MDktN2IxOS00OGEyLWFmMjktY2FiMmZkNWIyODZiXkEyXkFqcGdeQXVyMTMxODk2OTU@._V1_SY150_CR0,0,101,150_.jpg%27%7D'}, {'name': 'Back to the Future', 'picurl': 'https://m.media-amazon.com/images/M/MV5BZmU0M2Y1OGUtZjIxNi00ZjBkLTg1MjgtOWIyNThiZWIwYjRiXkEyXkFqcGdeQXVyMTQxNzMzNDI@._V1_SX101_CR0,0,101,150_.jpg%27%7D'}, {'name': 'Das Boot', 'picurl': 'https://m.media-amazon.com/images/M/MV5BOGZhZDIzNWMtNjkxMS00MDQ1LThkMTYtZWQzYWU3MWMxMGU5XkEyXkFqcGdeQXVyNjc1NTYyMjg@._V1_SX101_CR0,0,101,150_.jpg%27%7D'}, {'name': 'Inglourious Basterds', 'picurl': 'https://m.media-amazon.com/images/M/MV5BOTJiNDEzOWYtMTVjOC00ZjlmLWE0NGMtZmE1OWVmZDQ2OWJhXkEyXkFqcGdeQXVyNTIzOTk5ODM@._V1_SY150_CR0,0,101,150_.jpg%27%7D'}, {'name': '2001: A Space Odyssey', 'picurl': 'https://m.media-amazon.com/images/M/MV5BMmNlYzRiNDctZWNhMi00MzI4LThkZTctMTUzMmZkMmFmNThmXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SY150_CR0,0,101,150_.jpg%27%7D'}, {'name': 'North by Northwest', 'picurl': 'https://m.media-amazon.com/images/M/MV5BZDA3NDExMTUtMDlhOC00MmQ5LWExZGUtYmI1NGVlZWI4OWNiXkEyXkFqcGdeQXVyNjc1NTYyMjg@._V1_SX101_CR0,0,101,150_.jpg%27%7D'}],
          'Comedy':[{'name': 'Life Is Beautiful', 'picurl': 'https://m.media-amazon.com/images/M/MV5BYmJmM2Q4NmMtYThmNC00ZjRlLWEyZmItZTIwOTBlZDQ3NTQ1XkEyXkFqcGdeQXVyMTQxNzMzNDI@._V1_SX101_CR0,0,101,150_.jpg'}, {'name': 'Parasite', 'picurl': 'https://m.media-amazon.com/images/M/MV5BYWZjMjk3ZTItODQ2ZC00NTY5LWE0ZDYtZTI3MjcwN2Q5NTVkXkEyXkFqcGdeQXVyODk4OTc3MTY@._V1_SY150_CR0,0,101,150_.jpg'}, {'name': 'Modern Times', 'picurl': 'https://m.media-amazon.com/images/M/MV5BYjJiZjMzYzktNjU0NS00OTkxLWEwYzItYzdhYWJjN2QzMTRlL2ltYWdlL2ltYWdlXkEyXkFqcGdeQXVyNjU0OTQ0OTY@._V1_SX101_CR0,0,101,150_.jpg'}, {'name': 'City Lights', 'picurl': 'https://m.media-amazon.com/images/M/MV5BY2I4MmM1N2EtM2YzOS00OWUzLTkzYzctNDc5NDg2N2IyODJmXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SX101_CR0,0,101,150_.jpg'}, {'name': 'The Great Dictator', 'picurl': 'https://m.media-amazon.com/images/M/MV5BMmExYWJjNTktNGUyZS00ODhmLTkxYzAtNWIzOGEyMGNiMmUwXkEyXkFqcGdeQXVyNjU0OTQ0OTY@._V1_SY150_CR0,0,101,150_.jpg'}, {'name': 'Dr. Strangelove or: How I Learned to Stop Worrying and Love the Bomb', 'picurl': 'https://m.media-amazon.com/images/M/MV5BZWI3ZTMxNjctMjdlNS00NmUwLWFiM2YtZDUyY2I3N2MxYTE0XkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SX101_CR0,0,101,150_.jpg'}],
          'Drama':[{'name': 'The Godfather', 'picurl': 'https://m.media-amazon.com/images/M/MV5BM2MyNjYxNmUtYTAwNi00MTYxLWJmNWYtYzZlODY3ZTk3OTFlXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SY150_CR2,0,101,150_.jpg'}, {'name': 'The Godfather: Part II', 'picurl': 'https://m.media-amazon.com/images/M/MV5BMWMwMGQzZTItY2JlNC00OWZiLWIyMDctNDk2ZDQ2YjRjMWQ0XkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SY150_CR2,0,101,150_.jpg'}, {'name': '12 Angry Men', 'picurl': 'https://m.media-amazon.com/images/M/MV5BMWU4N2FjNzYtNTVkNC00NzQ0LTg0MjAtYTJlMjFhNGUxZDFmXkEyXkFqcGdeQXVyNjc1NTYyMjg@._V1_SX101_CR0,0,101,150_.jpg'}, {'name': 'Pulp Fiction', 'picurl': 'https://m.media-amazon.com/images/M/MV5BNGNhMDIzZTUtNTBlZi00MTRlLWFjM2ItYzViMjE3YzI5MjljXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SY150_CR1,0,101,150_.jpg'}, {'name': 'Se7en', 'picurl': 'https://m.media-amazon.com/images/M/MV5BOTUwODM5MTctZjczMi00OTk4LTg3NWUtNmVhMTAzNTNjYjcyXkEyXkFqcGdeQXVyNjU0OTQ0OTY@._V1_SX101_CR0,0,101,150_.jpg'}, {'name': 'City of God', 'picurl': 'https://m.media-amazon.com/images/M/MV5BOTMwYjc5ZmItYTFjZC00ZGQ3LTlkNTMtMjZiNTZlMWQzNzI5XkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SX101_CR0,0,101,150_.jpg'}],
          'Crime':[{'name': 'The Godfather', 'picurl': 'https://m.media-amazon.com/images/M/MV5BM2MyNjYxNmUtYTAwNi00MTYxLWJmNWYtYzZlODY3ZTk3OTFlXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SY150_CR2,0,101,150_.jpg'}, {'name': 'The Godfather: Part II', 'picurl': 'https://m.media-amazon.com/images/M/MV5BMWMwMGQzZTItY2JlNC00OWZiLWIyMDctNDk2ZDQ2YjRjMWQ0XkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SY150_CR2,0,101,150_.jpg'}, {'name': '12 Angry Men', 'picurl': 'https://m.media-amazon.com/images/M/MV5BMWU4N2FjNzYtNTVkNC00NzQ0LTg0MjAtYTJlMjFhNGUxZDFmXkEyXkFqcGdeQXVyNjc1NTYyMjg@._V1_SX101_CR0,0,101,150_.jpg'}, {'name': 'Pulp Fiction', 'picurl': 'https://m.media-amazon.com/images/M/MV5BNGNhMDIzZTUtNTBlZi00MTRlLWFjM2ItYzViMjE3YzI5MjljXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SY150_CR1,0,101,150_.jpg'}, {'name': 'Se7en', 'picurl': 'https://m.media-amazon.com/images/M/MV5BOTUwODM5MTctZjczMi00OTk4LTg3NWUtNmVhMTAzNTNjYjcyXkEyXkFqcGdeQXVyNjU0OTQ0OTY@._V1_SX101_CR0,0,101,150_.jpg'}, {'name': 'City of God', 'picurl': 'https://m.media-amazon.com/images/M/MV5BOTMwYjc5ZmItYTFjZC00ZGQ3LTlkNTMtMjZiNTZlMWQzNzI5XkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SX101_CR0,0,101,150_.jpg'}],
          'Action':[{'name': 'The Dark Knight', 'picurl': 'https://m.media-amazon.com/images/M/MV5BMTMxNTMwODM0NF5BMl5BanBnXkFtZTcwODAyMTk2Mw@@._V1_SY150_CR0,0,101,150_.jpg'}, {'name': 'The Lord of the Rings: The Return of the King', 'picurl': 'https://m.media-amazon.com/images/M/MV5BNzA5ZDNlZWMtM2NhNS00NDJjLTk4NDItYTRmY2EwMWZlMTY3XkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SY150_CR0,0,101,150_.jpg'}, {'name': 'The Lord of the Rings: The Fellowship of the Ring', 'picurl': 'https://m.media-amazon.com/images/M/MV5BN2EyZjM3NzUtNWUzMi00MTgxLWI0NTctMzY4M2VlOTdjZWRiXkEyXkFqcGdeQXVyNDUzOTQ5MjY@._V1_SY150_CR0,0,101,150_.jpg'}, {'name': 'Inception', 'picurl': 'https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@._V1_SY150_CR0,0,101,150_.jpg'}, {'name': 'Star Wars: Episode V - The Empire Strikes Back', 'picurl': 'https://m.media-amazon.com/images/M/MV5BYmU1NDRjNDgtMzhiMi00NjZmLTg5NGItZDNiZjU5NTU4OTE0XkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SX101_CR0,0,101,150_.jpg'}, {'name': 'The Lord of the Rings: The Two Towers', 'picurl': 'https://m.media-amazon.com/images/M/MV5BZGMxZTdjZmYtMmE2Ni00ZTdkLWI5NTgtNjlmMjBiNzU2MmI5XkEyXkFqcGdeQXVyNjU0OTQ0OTY@._V1_SX101_CR0,0,101,150_.jpg'}],
          'Biography':[{'name': "Schindler's List", 'picurl': 'https://m.media-amazon.com/images/M/MV5BNDE4OTMxMTctNmRhYy00NWE2LTg3YzItYTk3M2UwOTU5Njg4XkEyXkFqcGdeQXVyNjU0OTQ0OTY@._V1_SX101_CR0,0,101,150_.jpg'}, {'name': 'Goodfellas', 'picurl': 'https://m.media-amazon.com/images/M/MV5BY2NkZjEzMDgtN2RjYy00YzM1LWI4ZmQtMjIwYjFjNmI3ZGEwXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SX101_CR0,0,101,150_.jpg'}, {'name': 'Hamilton', 'picurl': 'https://m.media-amazon.com/images/M/MV5BNjViNWRjYWEtZTI0NC00N2E3LTk0NGQtMjY4NTM3OGNkZjY0XkEyXkFqcGdeQXVyMjUxMTY3ODM@._V1_SY150_CR0,0,101,150_.jpg'}, {'name': 'The Pianist', 'picurl': 'https://m.media-amazon.com/images/M/MV5BOWRiZDIxZjktMTA1NC00MDQ2LWEzMjUtMTliZmY3NjQ3ODJiXkEyXkFqcGdeQXVyNjU0OTQ0OTY@._V1_SY150_CR4,0,101,150_.jpg'}, {'name': 'The Intouchables', 'picurl': 'https://m.media-amazon.com/images/M/MV5BMTYxNDA3MDQwNl5BMl5BanBnXkFtZTcwNTU4Mzc1Nw@@._V1_SY150_CR0,0,101,150_.jpg'}, {'name': 'Braveheart', 'picurl': 'https://m.media-amazon.com/images/M/MV5BMzkzMmU0YTYtOWM3My00YzBmLWI0YzctOGYyNTkwMWE5MTJkXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SY150_CR0,0,101,150_.jpg'}]}


def index(response, id):
	ls = MoviesToWatch.objects.get(id=id)
	return render(response, "main/list.html", {"ls":ls})

def home(response):
	return render(response, "main/home.html",{})
def topcharts(response, genre):
	l1 = topchart[genre]
	d1={}
	for i in l1:
		d1[i['name']]=i['picurl']
		#title+=[i['name'],]
		#picurl+=[i['picurl'],]
	return render(response, "main/topcharts.html", {'dict1':d1, 'genre':genre})

def suggest(response,name):
	movies=get_recommendation(name)
	if response.user.is_authenticated:
		return render(response, 'main/suggest.html', {'name':name, 'Movies':movies})
	return render(response, 'main/home.html', {'msg':'Please login!'})

def genre(response):
	return render(response,'main/getgenre.html')

def searchByGenre(response,genre):
	listofmov = genreSearch(str(genre))
	tupleofdata = []
	for i in listofmov:
		tupleofdata.append(tuple(i.values()))
	return render(response,'main/genres.html',{'data':tuple(tupleofdata),'genre':genre})
	


def search(request):
	if request.method=='POST':
		name=request.POST.get('name')
		results=searchMovie(name)
		names=[]
		for i in results:
			names.append(i.values())
		if names==[]:
			msg='No movie found with that name.'
		else:
			msg='Search results for {}:'.format(name)
		username=None
		if request.user.is_authenticated:
			username = request.user.username	
		return render(request,'main/search.html', {'uid':username,'name':name, 'Movies':tuple(names),'msg':msg})
	else:
		username=None
		if request.user.is_authenticated:
			username = request.user.username
			return render(request,'main/search.html',{'uid':username})
		return render(request, 'main/home.html')


def detail(response,id):
	username=None
	#print(id)
	if response.user.is_authenticated:
		try:
			print('in try block')
			det= get_details(id)
			movies=get_recommendation(det['title'])
			det.update({'Movies':movies})
			return render(response, 'main/detail.html',det)
		except:
			username=None
			if response.user.is_authenticated:
				username = response.user.username
				return redirect('/search')
	return redirect('/login',{'msg':'Please login!'})

def searchDet(request):
	if request.method=='POST':
		name=request.POST.get('name')
		print(name)
		return redirect('/detail/'+name)
	else:
		username=None
		if request.user.is_authenticated:
			username = request.user.username
			return render(request,'main/search_movie.html',{'uid':username})
		return render(request, 'main/home.html')

def index(response):
	if response.user.is_authenticated:
		username = response.user.username
		return render(response,'main/try_new.html',{'uid':username})
	return render(response, 'main/home.html', {'msg':'Please login!'})

def logout_view(request):
    logout(request)
    return render(request, 'main/home.html', {'msg':'You have been logged out!'})

def surprise(response):
	x= random.choice(['Comedy','Action','Adventure', 'Crime', 'Biography','Drama'])
	l1 = topchart[x]
	d1={}
	for i in l1:
		d1[i['name']]=i['picurl']
		#title+=[i['name'],]
		#picurl+=[i['picurl'],]
	return render(response, "main/surprise.html", {'dict1':d1, 'genre':'Surprise genre: '+x})


def genreSearch(genre):
    ia = imdb.IMDb()
    top = ia.get_top250_movies()
    listOfMovies = []
    ctr = 0
    for i in top:
        if ctr ==5:
            break
        filmID = i.getID()
        filmObj = ia.get_movie(filmID)
        if genre in filmObj.get('genres'):
            listOfMovies.append({'name':filmObj.get('title'),'year':filmObj.get('year'),'picurl':filmObj.get('cover url')})
            if listOfMovies[ctr]['picurl']==None:
                listOfMovies[ctr]['picurl']="https://watch--next.herokuapp.com/static/default.png"
            ctr+=1
    return listOfMovies