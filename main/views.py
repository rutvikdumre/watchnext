# views.py
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from .models import MoviesToWatch, Movie

# Create your views here.

def index(response, id):
	ls = MoviesToWatch.objects.get(id=id)
	return render(response, "main/list.html", {"ls":ls})

def home(response):
	return render(response, "main/home.html", {})
