"""
URL configuration for routes app.
"""
from django.urls import path
from routes.views import OptimizeRouteView


urlpatterns = [
    path('optimize-route/', OptimizeRouteView.as_view(), name='optimize-route'),
]

