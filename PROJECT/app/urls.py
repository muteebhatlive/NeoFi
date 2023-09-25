from django.urls import path
from .views import register,login,logout, online_users, start, send
from . import consumers

urlpatterns = [
    path('register/',register, name='register'),
    path('login/',login, name='login'),
    path('logout/',logout, name='logout'),
    path('online_users/',online_users, name='online_users'),
    path('chat/start/',start, name='start'),
    path('chat/send/', send, name='send'),
    path('ws/chat/', consumers.EchoConsumer.as_asgi()),


    ]