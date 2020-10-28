# views.py
import imdb
from django.contrib.auth import logout
from django.shortcuts import render,redirect
from django.http import HttpResponse, HttpResponseRedirect
from .models import MoviesToWatch, Movie
from  .wp_model import get_recommendation, get_details, searchMovie, genreSearch
# Create your views here.

def index(response, id):
	ls = MoviesToWatch.objects.get(id=id)
	return render(response, "main/list.html", {"ls":ls})

def home(response):
	return render(response, "main/home.html", {})

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
		username=None
		if request.user.is_authenticated:
			username = request.user.username	
		return render(request,'main/search.html', {'uid':username,'name':name, 'Movies':tuple(names),'msg':'Search results for {}:'.format(name)})
	else:
		username=None
		if request.user.is_authenticated:
			username = request.user.username
			return render(request,'main/search.html',{'uid':username})
		return render(request, 'main/home.html')
def detail(response,id):
	if response.user.is_authenticated:
		try:
			det= get_details(id)
			movies=get_recommendation(det['title'])
			det.update({'Movies':movies})
			return render(response, 'main/detail.html',det)
		except:
			username=None
			if response.user.is_authenticated:
				username = response.user.username
				return redirect('/search')
	return render(response, 'main/home.html', {'msg':'Please login!'})

def searchDet(request):
	if request.method=='POST':
		name=request.POST.get('name')
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