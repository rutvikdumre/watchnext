from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import RegisterForm


def register(response):
    if response.method == 'POST':
        form = RegisterForm(response.POST)
        if form.is_valid():
            user = form.save()
            login(response, user)
            return redirect('/index/')
    else:
        form = RegisterForm()
    return render(response, "register.html", {'form': form})
