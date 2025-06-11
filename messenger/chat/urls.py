from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('banned/', views.banned_page, name='banned_page'),
    path('delete_message/<int:message_id>/', views.delete_message, name='delete_message'),

    path('api/online_users/', views.online_users_api, name='online_users_api'),
    path('api/update_activity/', views.update_activity, name='update_activity'),

    path('room/<int:room_id>/leave/', views.leave_room, name='leave_room'),
    
    path('room/<int:room_id>/manage/', views.manage_room, name='manage_room'),
    path('invitations/', views.invitations_list, name='invitations_list'),
    path('invitation/<int:invitation_id>/', views.handle_invitation, name='handle_invitation'),

    path('global/', views.global_chat, name='global_chat'),

    path('api/messages/', views.MessageList.as_view(), name='message-list'),
    
    path('', views.chat_rooms, name='chat_rooms'),
    path('room/<int:room_id>/', views.room_detail, name='room_detail'),
    path('create/', views.create_room, name='create_room'),
    
    # Аутентификация
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register, name='register'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate_account'),


    path('room/<int:room_id>/delete/', views.delete_room, name='delete_room'),
    path('room/<int:room_id>/manage/', views.manage_room, name='manage_room'),

    path('profile/', views.profile_view, name='profile'),
]