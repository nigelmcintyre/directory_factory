from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from directory.sitemaps import LandingPageSitemap, ListingSitemap
from blog.sitemaps import BlogSitemap
from directory import views as directory_views

sitemaps = {
    "pages": LandingPageSitemap,
    "listings": ListingSitemap,
    "blog": BlogSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("blog/", include("blog.urls")),
    path("robots.txt", directory_views.robots_txt, name="robots_txt"),
    path("ads.txt", directory_views.ads_txt, name="ads_txt"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("", include("directory.urls")),
]
