"""mystranger URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls import include
from django.urls import path
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from mystranger_app.views import *
from account.views import (
    register_view,
    login_view,
    logout_view,
    account_search_view,
)

from nrt.views import *
from qna.views import *
from django.views.generic import TemplateView

handler404 = 'mystranger_app.views.error_404_view'

urlpatterns = [
    path('evilstranger666/', admin.site.urls),
    path('home/', home_view, name='home' ),
    path('', new_home_view, name='new-home' ),
    path('new_chat/', new_chat_view , name='new-chat' ),
    path('new_chat_text/', new_chat_text_view , name='new-chat-text' ),
    path('nrt_text/', nrt_text_view , name='nrt-text' ),
    path('nrt_text/how', nrt_text_how_view , name='nrt-text-how' ),
    path('nrt_text/wow', nrt_text_wow_view , name='nrt-text-wow' ),

    # path('notif-token/', save_token, name="notif-token"),
    path('notif-token/', notif_token_view, name="notif-token"),
    path('firebase-messaging-sw.js', service_worker, name='service_worker'),

    # path('send_push', send_push),
    # path('webpush/', include('webpush.urls')),
    # path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/x-javascript')),
    # path('firebase-messaging-sw.js/',showFirebaseJS,name="show_firebase_js"),


    path('search/', account_search_view, name="search"),
    path('feedback/', feedback_view, name="feedback"),
    path('privacy_policy/', privacy_policy_view, name="privacy-policy"),
    path('delete_account/', delete_account_view, name="delete-account"),
    path('aboutus/', aboutus_view, name="about-us"),
    path('terms/', terms_view, name="terms-conditions"),
    
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),

    path('account/', include('account.urls', namespace='account')),
    path('vibes/', include('qna.urls', namespace='qna')),
    path('confessions/', include('confessions.urls', namespace='confessions')),

    # Friend System
    path('friend/', include('friend.urls', namespace='friend')),

    # Public Chat App
    path('chat/', include('chat.urls', namespace='chat')),

    # Password reset links (ref: https://github.com/django/django/blob/master/django/contrib/auth/views.py)
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='password_reset/password_change_done.html'),
         name='password_change_done'),

    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='password_reset/password_change.html'),
         name='password_change'),

    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset/password_reset_form.html'), name='password_reset'),

    path('password_reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset/password_reset_done.html'),
    name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset/password_reset_change_form.html'), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset/password_reset_complete.html'),
    name='password_reset_complete'),

    # -------------------------------------
    

]



if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    