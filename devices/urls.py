from django.urls import path
from . import views

urlpatterns = [
    path('', views.navigate, name='navigate'),  # Default page (navigate)
    path('get_all_ship_locations/', views.get_all_ship_locations, name='get_locations'),
    path('get_live_ship_location/', views.get_live_ship_location, name='get_live_ship_location'),
    path('get_weather_data/', views.get_weather_data, name='get_weather'),
    path('search/', views.search_ship, name='search_device'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('devices/', views.list_devices, name='list_devices'),
    path('devices/add/', views.add_device, name='add_device'),
    path('devices/<int:device_id>/delete/', views.delete_device, name='delete_device'),
    path('home/', views.home_view, name='home'),  # Home page accessible only after login
    path('navigate/end/', views.navigate_end, name='navigate_end'),  # End navigation page
]
from django.conf import settings
from django.conf.urls.static import static


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)