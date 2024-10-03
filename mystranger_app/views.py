from django.shortcuts import render, redirect
from mystranger_app.models import Feedback
from mystranger_app.models import University, UniversityProfile
from django.http import HttpResponse
from account.models import Account , deleted_account
from django.contrib.auth import authenticate
from django.core.mail import send_mail

from django.http.response import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.http.response import HttpResponse
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404

from django.views.decorators.csrf import csrf_exempt
from webpush import send_user_notification
import json
from django.conf import settings
from django.http import HttpResponse
import requests

from django.http import HttpResponse
import os
from fcm_django.models import FCMDevice
from django_user_agents.utils import get_user_agent
from notification.models import ActiveVideoUsers




def service_worker(request):
    file_path = os.path.join(os.path.dirname(__file__), 'firebase-messaging-sw.js')
    print()
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/javascript')
        response['Content-Disposition'] = 'inline; filename=firebase-messaging-sw.js'
        return response

@csrf_exempt
def notif_token_view(request):
    
    if request.method=='POST':

        try:
            token = request.POST.get('token')
            print('The token is -', token)

            user = request.user

            my_ac = Account.objects.get(id=request.user.id)
            my_ac.ntoken = token
            my_ac.save()

            print('the token is saved into db - ', token)

            response_data = {
                        'status' : 'success',
                        'message': 'token added',
                        'token' : token,
                    }
            
        except Exception as e :
                print('error fetching the answer')
                response_data = {
                'status' : 'error',
                'message': str(e),
            }
    return HttpResponse(json.dumps(response_data), content_type="application/json")      


@csrf_exempt
def save_token(request):

    if request.method == 'POST':

        try:
            token = request.POST.get('token')
            # device_type = request.POST.get('device_type')  # 'web', 'mobile', etc.
            user = request.user  # get the currently logged in user
            user_agent = get_user_agent(request)
            if user_agent.is_mobile:
                device_type = 'mobile'
            elif user_agent.is_tablet:
                device_type = 'tablet'
            else:
                device_type = 'desktop'


            device = FCMDevice.objects.create(user=user, registration_id=token, type=device_type)
            print('the token is saved into db')

            response_data = {
                        'status' : 'success',
                        'message': 'token added',
                        'token' : token,
                    }
            
        except Exception as e :
                print('error fetching the answer - ', str(e))
                response_data = {
                'status' : 'error',
                'message': str(e),
            }

        return HttpResponse(json.dumps(response_data), content_type="application/json")   



# @require_POST
# @csrf_exempt
# def send_push(request):
#     try:
#         body = request.body
#         data = json.loads(body)

#         if 'head' not in data or 'body' not in data or 'id' not in data:
#             return JsonResponse(status=400, data={"message": "Invalid data format"})

#         user_id = data['id']
#         user = get_object_or_404(Account, pk=user_id)
#         print('i am the user, ', user)
#         # payload = {'head': data['head'], 'body': data['body']}
#         payload = {'head': 'Test Head', 'body': 'Test Body'}
        
#         send_user_notification(user=user, payload=payload, ttl=1000)
#         print('notif pushed - ')

#         return JsonResponse(status=200, data={"message": "Web push successful"})
#     except TypeError:
#         return JsonResponse(status=500, data={"message": "An error occurred"})

# def send(request):
#     resgistration  = [
#     ]
#     send_notification(resgistration , 'Code Keen added a new video' , 'Code Keen new video alert')
#     return HttpResponse("sent")


# def send_notification(registration_ids , message_title , message_desc):
#     fcm_api = "BL5fFXV5nBLXhDblD0qWii5Pg7ED211JJQxweRVBAg9qS1RrhhfO36L7PvpnVtbkCpiNNc18VSeisDGrBpobYqs"
#     url = "https://fcm.googleapis.com/fcm/send"
    
#     headers = {
#     "Content-Type":"application/json",
#     "Authorization": 'key='+fcm_api}

#     payload = {
#         "registration_ids" :registration_ids,
#         "priority" : "high",
#         "notification" : {
#             "body" : message_desc,
#             "title" : message_title,
#             "image" : "https://i.ytimg.com/vi/m5WUPHRgdOA/hqdefault.jpg?sqp=-oaymwEXCOADEI4CSFryq4qpAwkIARUAAIhCGAE=&rs=AOn4CLDwz-yjKEdwxvKjwMANGk5BedCOXQ",
#             "icon": "https://yt3.ggpht.com/ytc/AKedOLSMvoy4DeAVkMSAuiuaBdIGKC7a5Ib75bKzKO3jHg=s900-c-k-c0x00ffffff-no-rj",
            
#         }
#     }

#     result = requests.post(url,  data=json.dumps(payload), headers=headers )
#     print(result.json())





# def showFirebaseJS(request):
#     data='importScripts("https://www.gstatic.com/firebasejs/8.2.0/firebase-app.js");' \
#          'importScripts("https://www.gstatic.com/firebasejs/8.2.0/firebase-messaging.js"); ' \
#          'var firebaseConfig = {' \
#          '        apiKey: "AIzaSyDyNyMD0b0BHTzMj-mULfQW9qc2lwh6CmU",' \
#          '        authDomain: "mystranger4.firebaseapp.com",' \
#          '        projectId: "mystranger4",' \
#          '        storageBucket: "mystranger4.appspot.com",' \
#          '        messagingSenderId: "547419092017",' \
#          '        appId: "1:547419092017:web:3db968cbd00da61eff9110",' \
#          '        measurementId: "G-3HZ2RQV1PT"' \
#          ' };' \
#          'firebase.initializeApp(firebaseConfig);' \
#          'const messaging=firebase.messaging();' \
#          'messaging.setBackgroundMessageHandler(function (payload) {' \
#          '    console.log(payload);' \
#          '    const notification=JSON.parse(payload);' \
#          '    const notificationOption={' \
#          '        body:notification.body,' \
#          '        icon:notification.icon' \
#          '    };' \
#          '    return self.registration.showNotification(payload.notification.title,notificationOption);' \
#          '});'
    
#     response = HttpResponse(data, content_type='application/javascript')
#     response['Content-Disposition'] = 'inline; filename=firebase-messaging-sw.js'
#     return response

    # return HttpResponse(data,content_type="text/javascript")

# Create your views here.
def new_home_view(request):
    if request.user.is_authenticated:
        return redirect('qna:pika')
    else:
        return redirect('home')

# Create your views here.
def home_view(request):

    context = {}
    context['is_active'] = 'home'
    if request.user.is_authenticated:
        user = request.user
        user.update_last_activity()
        # checking if user's uni exist or the user is using uni prof instead
        uni_name = user.university_name

        text_count = create_text_count(request.user)
        if text_count == 1 or text_count==None:
            text_count = 1

        video_count = create_video_count(request.user)
        if video_count == 1 or video_count==None:
            video_count = 1

        context['texti_counti'] = text_count
        context['videoi_counti'] = video_count

        try:
            universi = University.objects.get(name=uni_name)
        except University.DoesNotExist:
            try:
                universi_prof = UniversityProfile.objects.get(name=uni_name)
                context['unverified_uni'] = 'True'
                context['prof_email'] = universi_prof.name
                context['prof_name'] = universi_prof.universityName
            except UniversityProfile.DoesNotExist:
                print('something went wrong....')
    return render(request,'home.html', context)

def new_chat_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    return render(request,'new_chat.html')
    
def new_chat_text_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    context={}
    token = request.user.ntoken
    if token == 'None':
        print('the token is none bro - ', token)
    elif token == ' ':
        pass
    elif len(str(token)) > 10:
        print('the token does exist - ', token)
        context['token_exist'] = 'yes'
    return render(request,'new_chat_text.html',context)

def error_404_view(request, exception):
    return render(request, 'error_404.html')

def feedback_view(request):

    if not request.user.is_authenticated:
        return redirect("login")
    
    context = {}
    if request.method == 'POST':

        message = request.POST.get('message')
        user = request.user
        feedback = Feedback(user = user, message = message)
        feedback.save()
        context['response'] = "We've recieved your message....."
        # context['msg'] = "It may not a big deal for you but for us it is"


    return render(request,'feedback_form.html',context)


def privacy_policy_view(request):
    return render(request, 'privacy_policy.html')

def delete_account_view(request):

    user = request.user
    context = {}
    if not user.is_authenticated:
        return redirect('login')
    
    if request.method=='POST':

        password = request.POST.get('password')
        reason = request.POST.get('txt')

        email = user.email
        account = authenticate(email=email, password=password)
        if account:
            deleted_account_obj = deleted_account(email=email, name=user.name, reason = reason)
            deleted_account_obj.save()
            account.delete()
            send_email_view(request, email)
            # return render(request, 'account_deleted.html')
            return HttpResponse("""
                    <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Account Deleted!</title>
                        </head>
                        <body>
                                <div class="container">

                            <div class="">
                                <div class="h-100 p-5 bg-body-tertiary border rounded-3" style='text-align:center;'>
                                <h2>Your Account Has Been Successfully Deleted!</h2>
                                <p class="" style="font-size:18px; margin-top:0.5em;">You'll recieve an email from <a href="https://mystranger.in/">mystranger.in</a> informing you about your account deletion.</p>
                                </div>
                            </div>

                        </div>
                        </body>
                        </html>
                    """)
        else:
            context['wrong'] = 'The password you have entered is incorrect! '
            return render(request, 'delete_account.html', context)

    return render(request, 'delete_account.html', context)

def aboutus_view(request):
    return HttpResponse('About Us view')

def terms_view(request):
    return render(request, 'terms.html')


def send_email_view(request, email):
    try:

        subject = 'MyStranger | Your account has been deleted!'
        message = f"We are deeply sorry that you don't like mystranger.in | You are alway's welcome to create your account again by visiting https://mystranger.in/register | If you haven't deleted your account on mystranger.in and still getting this mail than either reply back or send a mail to info@mystranger.in."
        # message = f'Hi paste the link to verify your account http://127.0.0.1:8000/account/verify/{token}'
        from_email = 'info@mystranger.in'
        recipient_list = [email]
        send_mail(subject, message, from_email, recipient_list)
        
    except Exception as e:
        print(e)


def create_video_count(user):
    uni_name = user.university_name
    try:
        count = 0
        universi = University.objects.get(name=uni_name)
        active_video_obj = ActiveVideoUsers.objects.get(pk=1)
        active_users = active_video_obj.users.all()
        for user in active_users:
            if user in universi.allNearbyUsers.all():
                count += 1
        return count
    except University.DoesNotExist:
        try:
            count = 0
            universi_prof = UniversityProfile.objects.get(name=uni_name)
            active_video_obj = ActiveVideoUsers.objects.get(pk=1)
            active_users = active_video_obj.users.all()
            for user in active_users:
                if user in universi_prof.allNearbyUsers.all():
                    count += 1
            return count
           
        except UniversityProfile.DoesNotExist:
            print('something went wrong....')


def create_text_count(user):
    uni_name = user.university_name
    try:
        count = 0
        universi = University.objects.get(name=uni_name)
        active_video_obj = ActiveVideoUsers.objects.get(pk=2)
        active_users = active_video_obj.users.all()
        for user in active_users:
            if user in universi.allNearbyUsers.all():
                count += 1
        return count
    except University.DoesNotExist:
        try:
            count = 0
            universi_prof = UniversityProfile.objects.get(name=uni_name)
            active_video_obj = ActiveVideoUsers.objects.get(pk=2)
            active_users = active_video_obj.users.all()
            for user in active_users:
                if user in universi_prof.allNearbyUsers.all():
                    count += 1
            return count
           
        except UniversityProfile.DoesNotExist:
            print('something went wrong....')
