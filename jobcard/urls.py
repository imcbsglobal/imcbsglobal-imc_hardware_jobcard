from django.urls import path
from . import views

urlpatterns = [
    path('', views.jobcard_list, name='jobcard_list'),
    path('create/', views.jobcard_create, name='jobcard_create'),
   path('<int:pk>/edit/', views.jobcard_edit, name='jobcard_edit'),

    path('delete/<int:pk>/', views.delete_jobcard, name='delete_jobcard'),
]