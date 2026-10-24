from django.contrib import admin

from .models import Item, Member, Vote, WatchList

admin.site.register([WatchList, Member, Item, Vote])
