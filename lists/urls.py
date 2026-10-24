from django.urls import path

from . import draw, views

app_name = 'lists'

urlpatterns = [
    path('', views.index, name='index'),
    path('new', views.create, name='create'),
    path('join/<str:code>', views.join, name='join'),
    path('<str:code>/', views.detail, name='detail'),
    path('<str:code>/state', views.state, name='state'),
    path('<str:code>/add', views.add, name='add'),
    path('<str:code>/pick', views.pick, name='pick'),
    path('<str:code>/leave', views.leave, name='leave'),
    path('<str:code>/hat/', draw.hat, name='hat'),
    path('<str:code>/hat/start', draw.start, name='hat_start'),
    path('<str:code>/hat/pick', draw.pick, name='hat_pick'),
    path('<str:code>/hat/unpick/<int:ticket_id>', draw.unpick, name='hat_unpick'),
    path('<str:code>/hat/draw', draw.draw, name='hat_draw'),
    path('<str:code>/items/<int:item_id>/vote', views.vote, name='vote'),
    path('<str:code>/items/<int:item_id>/watched', views.watched, name='watched'),
    path('<str:code>/items/<int:item_id>/remove', views.remove, name='remove'),
]
