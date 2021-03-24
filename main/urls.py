from django.urls import path
from . import views

urlpatterns = [

path("", views.home, name="home"),
path("topcharts/<str:genre>", views.topcharts, name="topcharts"),
path("logout/topcharts/<str:genre>", views.topcharts, name="topcharts"),
path("search/", views.searchDet, name="searchDet"),
path("suggest/", views.search, name="search"),
path("index/", views.index, name="index"),
path("suggestions/<str:name>",views.suggest, name="suggest"),
path("<int:id>", views.index, name="index"),
path("detail/<str:id>", views.detail, name="detail"),
path('logout/', views.logout_view, name='logout'),
path('genres/<str:genre>',views.searchByGenre,name='genresearch'),
path('searchgenre/',views.genre,name='searchbygenre')
]