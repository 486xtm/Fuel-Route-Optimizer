"""
URL configuration for routes app.
"""
from django.urls import path
from routes.views import OptimizeRouteView, IPLogView


urlpatterns = [
    path('optimize-route/', OptimizeRouteView.as_view(), name='optimize-route'),
    path('ip-logs/', IPLogView.as_view(), name='ip-logs'),
]

