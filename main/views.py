# views.py
from django.shortcuts import render
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
	movie=get_recommendation(name)
	return render(response, 'main/suggest.html', {'name':name, 'Movies':movie})
	
def search(request):
	if request.method=='POST':
		name=request.POST.get('name')
		results=searchMovie(name)
		names=[]
		for i in results:
			names.append(i.values())
			
		return render(request,'main/search.html', {'name':name, 'Movies':tuple(names)})
	return render(request,'main/search.html')
def detail(response,id):
	det= get_details(id)
	url=det['picurl']
	return render(response, 'main/detail.html',{'det':det.items(),'url':url})
	
