from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('supporthub.accounts.urls')),
    path('api/', include('supporthub.tickets.urls')),
]
