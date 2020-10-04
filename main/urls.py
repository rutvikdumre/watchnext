from django.urls import path
from . import views

urlpatterns = [

path("", views.home, name="home"),
path("suggest/", views.search, name="search"),
path("suggestions/<str:name>",views.suggest, name="suggest"),
path("<int:id>", views.index, name="index"),
path("detail/<str:id>", views.detail, name="detail"),
]