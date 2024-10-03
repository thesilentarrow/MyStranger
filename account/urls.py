from django.urls import path

from account.views import (
	account_view,
    edit_account_view,
    # edit_pass_view,
    tokenSend,
    verify,
    nearby_uni,
    registration_error,
    nearby_uni_stud,
    prompt_view,
    resend_verif_view,
    
)

app_name = 'account'

urlpatterns = [
	path('<user_id>/', account_view, name="view"),
    path('<user_id>/edit/', edit_account_view, name='edit'),
    # path('<user_id>/edit-pass/', edit_pass_view, name='edit-pass'),

	path('register/token/', tokenSend, name="token"),
    path('verify/<auth_token>' , verify , name="verify"),
    path('nearby/universities' , nearby_uni , name="nearby-uni"),
    path('nearby/uni-students/<uni_id>' , nearby_uni_stud , name="nearby-uni-stud"),
    path('registration/issueForm' , registration_error , name="reg-error"),
    path('prompt/view' , prompt_view , name="prompt"),
    path('resend/verification_email' , resend_verif_view , name="resend-verif"),
    
    
]