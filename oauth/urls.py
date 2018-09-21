from .views import join,callback
from django.urls import path

urlpatterns=[
    path('join/',join),
    path('callback/',callback)
]
