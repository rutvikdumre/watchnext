# views.py
from django.contrib.auth import logout
from django.shortcuts import render,redirect
from django.http import HttpResponse, HttpResponseRedirect
from .models import MoviesToWatch, Movie
from  .wp_model import get_recommendation, get_details, searchMovie
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
		return render(request,'main/search.html', {'uid':username,'name':name, 'Movies':tuple(names),'msg':'Did you mean:'})
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
		return render(response,'main/index.html',{'uid':username})
	return render(response, 'main/home.html', {'msg':'Please login!'})

def logout_view(request):
    logout(request)
    return render(request, 'main/home.html', {'msg':'You have been logged out!'})