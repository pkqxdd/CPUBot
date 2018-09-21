from django.urls import path,include
from django.http import HttpResponseRedirect

urlpatterns = [
    path('api/',include('oauth.urls')),
    path('',lambda r:HttpResponseRedirect("https://cpu.party/join/"))
]
