import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


def new_code():
    return secrets.token_urlsafe(6)


class WatchList(models.Model):
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=16, unique=True, default=new_code)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

    def touch(self):
        """Mark the list as changed so other open tabs refresh."""
        self.updated_at = timezone.now()
        WatchList.objects.filter(pk=self.pk).update(updated_at=self.updated_at)


class Member(models.Model):
    watchlist = models.ForeignKey(WatchList, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    guest_token = models.CharField(max_length=40, blank=True, db_index=True)
    name = models.CharField(max_length=40)
    is_owner = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['joined_at']

    def __str__(self):
        return self.name


class Item(models.Model):
    watchlist = models.ForeignKey(WatchList, on_delete=models.CASCADE, related_name='items')
    imdb_id = models.CharField(max_length=12)
    title = models.CharField(max_length=300)
    year = models.CharField(max_length=10, blank=True)
    poster = models.CharField(max_length=500, blank=True)
    added_by = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    added_at = models.DateTimeField(auto_now_add=True)
    watched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-added_at']
        constraints = [models.UniqueConstraint(fields=['watchlist', 'imdb_id'], name='unique_movie_per_list')]

    def __str__(self):
        return self.title


class Vote(models.Model):
    WANT, PASS = 1, -1
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='votes')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='votes')
    value = models.SmallIntegerField(choices=[(WANT, 'Want to watch'), (PASS, 'Pass')])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['item', 'member'], name='one_vote_per_member')]


class Round(models.Model):
    """A movie draw: everyone puts picks in the hat, then one ticket wins."""
    watchlist = models.ForeignKey(WatchList, on_delete=models.CASCADE, related_name='rounds')
    started_by = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    picks_per_person = models.PositiveSmallIntegerField(default=3)
    secret = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    drawn_at = models.DateTimeField(null=True, blank=True)
    drawn_by = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    winner = models.ForeignKey('Ticket', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        ordering = ['-created_at']


class Ticket(models.Model):
    """One person's pick. The same movie picked by two people = two tickets."""
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='tickets')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='tickets')
    imdb_id = models.CharField(max_length=12)
    title = models.CharField(max_length=300)
    year = models.CharField(max_length=10, blank=True)
    poster = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        constraints = [models.UniqueConstraint(fields=['round', 'member', 'imdb_id'], name='one_ticket_per_movie_per_member')]
