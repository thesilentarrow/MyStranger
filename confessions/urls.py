from django.urls import path
from confessions.views import *

app_name = 'confessions'

urlpatterns = [
    path('', pikac_view , name='pikac' ),
    path('create_post/', create_post_view, name='create-postc'),
    path('minichat/<user_id>/', minichat_view , name='minichatc' ),
    path('addAnswer/', addAnswer_view , name='addAnswerc' ),
    path('question/<ans_id>/', show_ques_view , name='question-viewc' ),
    path('cworking/', cworking_view , name='cworking' ),
    path('search/', search_view , name='search-view' ),
]