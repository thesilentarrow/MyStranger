from django.urls import path
from qna.views import *

app_name = 'qna'

urlpatterns = [
    path('', pika_view , name='pika' ),
    path('create_post/', create_post_view, name='create-post'),
    path('minichat/<user_id>/', minichat_view , name='minichat' ),
    path('addAnswer/', addAnswer_view , name='addAnswer' ),
    path('question/<ans_id>/', show_ques_view , name='question-view' ),
]