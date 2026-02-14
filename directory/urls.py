from django.urls import path
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("listing/<slug:slug>/", views.listing_detail, name="listing_detail"),
    path("<slug:city>/", views.pseo_landing, name="pseo_landing"),
]
