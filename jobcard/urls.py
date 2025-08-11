# urls.py (in your app directory)
from django.urls import path
from . import views

urlpatterns = [
    path('', views.jobcard_list, name='jobcard_list'),
    path('create/', views.jobcard_create, name='jobcard_create'),
    path('edit/<int:pk>/', views.jobcard_edit, name='jobcard_edit'),
    path('delete/<int:pk>/', views.delete_jobcard, name='delete_jobcard'),
    # NEW URL PATTERN for deleting by ticket number
    path('delete-ticket/<str:ticket_no>/', views.delete_ticket_by_number, name='delete_ticket_by_number'),
]