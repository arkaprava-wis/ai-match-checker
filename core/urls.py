from django.contrib import admin
from django.urls import path,include
from .views import *
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('roles/', RolesList.as_view(), name='roles'),
    path('roles/add/', RoleCreateView.as_view(), name='add-role'),
    path('roles/update/<int:pk>/', RoleUpdateView.as_view(), name='update-role'),
    
 

    
    path('franchise/', FranchiseList.as_view(), name='franchise'),
    path('franchise/add', FranchiseCreateView.as_view(), name='franchise_add'),
    path('franchise/update/<int:pk>/', FranchiseUpdateView.as_view(), name='franchise_update'),
    path('franchise/<int:pk>/delete/', FranchiseDeleteView.as_view(), name='franchise_delete'),
    path('franchise/<int:pk>/', FranchiseDetailView.as_view(), name='franchise_details'),
    

    path('users/', UsersList.as_view(), name='users'),
    path('users/add', AddUsers.as_view(), name='add-users'),
    path('ajax/add-user/', ajax_add_user, name='ajax_add_user'),
    
    path('users/edit/<int:pk>/', EditUsers.as_view(), name='edit-users'),
    path('ajax/edit-user/<int:pk>/', ajax_edit_user, name='ajax_edit_user'),
    
]
