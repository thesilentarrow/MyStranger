from django.shortcuts import render, redirect
from account.forms import RegistrationForm, AccountAuthenticationForm
from django.http import HttpResponse, HttpResponseBadRequest
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from account.models import Account
from mystranger_app.models import University, UniversityProfile , Flags
from friend.models import FriendList, FriendRequest
from django.db.models import Q
from mystranger_app.utils import calculate_distance
from friend.utils import get_friend_request_or_false
from friend.friend_request_status import FriendRequestStatus
from django.contrib.auth.hashers import make_password
from mystranger.settings import accesstoken
import json

#7nov12
import uuid
from account.models import AccountToken
from django.conf import settings
from django.core.mail import send_mail


def register_view(request, *args, **kwargs):

    user = request.user
    context = {}
    if user.is_authenticated:
        return HttpResponse(f'You are already authenticated as {user.name} with email - {user.email}')

    context['accesstoken'] = accesstoken

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()

            email = form.cleaned_data['email'].lower()
            raw_password = form.cleaned_data['password1']
            account = authenticate(email=email, password=raw_password)

            # add the university if not already added than add the user to that university
            name = email.split('@')[-1:][0]
            lat = request.POST.get('lat')
            lon = request.POST.get('lon')

            # we are creating or fetching the university model but if the info came from user input then we are going to create a university profile, the university model is only going to be created when either it came from the database or it is manually verified from the backend.

            notrust = request.POST.get('notrust')
            if notrust:
                # This means that location is obtained from the user input and can't be trusted therefore we are gonna create a university profile
                uniName = request.POST.get('universityName')
                university_profile = fetch_or_create_uniprofile(
                    name, lat, lon, uniName)
                university_profile.add_user(account)
            else:
                university = fetch_or_create_uni(name, lat, lon)
                university.add_user(account)
            
            # 7nov12
            auth_token = str(uuid.uuid4())
            account_token = AccountToken.objects.create(user = account, auth_token = auth_token)
            account_token.save()
            send_mail_after_registration(email , auth_token)


            # destination = kwargs.get('next')
            # if destination:
            #     return redirect(destination)
            # else:
            #     return redirect('home')
            
            return redirect('token')


            
            
        else:
            context['registration_form'] = form

    else:
        form = RegistrationForm()
        context['registration_form'] = form

    return render(request, 'account/register.html', context)


def logout_view(request):
    logout(request)
    return redirect('home')


def login_view(request, *args, **kwargs):

    context = {}
    user = request.user
    if user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AccountAuthenticationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            password = request.POST.get('password')
            user = authenticate(email=email, password=password)

            if user:
                user_token = AccountToken.objects.filter(user = user).first()
                if user_token.exists():
                    if user_token.is_verified:
                        login(request, user)
                        destination = kwargs.get('next')
                        if destination:
                            return redirect(destination)
                        else:
                            return redirect('home')
                    else:
                        context['unverified'] = 'Please verify your account!'
                        return render(request, 'account/login.html', context)
                  
        else:
            context['login_form'] = form

    return render(request, 'account/login.html', context)


def account_view(request, *args, **kwargs):
    """
    - Logic here is kind of tricky
            is_self (boolean)
                    is_friend (boolean)
                            -1: NO_REQUEST_SENT
                            0: THEM_SENT_TO_YOU
                            1: YOU_SENT_TO_THEM
    """
    context = {}
    user_id = kwargs.get("user_id")
    try:
        account = Account.objects.get(pk=user_id)
    except:
        return HttpResponse("Something went wrong.")
    if account:
        context['id'] = account.id
        context['name'] = account.name
        context['email'] = account.email
        context['origin'] = account.origin
        # context['universityName'] = account.universityName
        context['gender'] = account.gender

        try:
            friend_list = FriendList.objects.get(user=account)
        except FriendList.DoesNotExist:
            friend_list = FriendList(user=account)
            friend_list.save()

        friends = friend_list.friends.all()
        context['friends'] = friends

        # Define template variables
        is_self = True
        is_friend = False
        # range: ENUM -> friend/friend_request_status.FriendRequestStatus
        request_sent = FriendRequestStatus.NO_REQUEST_SENT.value
        friend_requests = None
        user = request.user

        if user.is_authenticated and user != account:
            is_self = False
            if friends.filter(pk=user.id):
                is_friend = True
            else:
                is_friend = False
                # CASE1: Request has been sent from THEM to YOU: FriendRequestStatus.THEM_SENT_TO_YOU
                if get_friend_request_or_false(sender=account, receiver=user) != False:
                    request_sent = FriendRequestStatus.THEM_SENT_TO_YOU.value
                    context['pending_friend_request_id'] = get_friend_request_or_false(
                        sender=account, receiver=user).id
                # CASE2: Request has been sent from YOU to THEM: FriendRequestStatus.YOU_SENT_TO_THEM
                elif get_friend_request_or_false(sender=user, receiver=account) != False:
                    request_sent = FriendRequestStatus.YOU_SENT_TO_THEM.value
                # CASE3: No request sent from YOU or THEM: FriendRequestStatus.NO_REQUEST_SENT
                else:
                    request_sent = FriendRequestStatus.NO_REQUEST_SENT.value
        elif not user.is_authenticated:
            is_self = False
        else:
            try:
                friend_requests = FriendRequest.objects.filter(
                    receiver=user, is_active=True)
            except:
                pass

        # Set the template variables to the values
        context['is_self'] = is_self
        context['is_friend'] = is_friend
        context['request_sent'] = request_sent
        context['friend_requests'] = friend_requests

        return render(request, "account/account.html", context)


def edit_account_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect("login")
    user_id = kwargs.get("user_id")
    account = Account.objects.get(pk=user_id)
    if account.pk != request.user.pk:
        return HttpResponse("You cannot edit someone elses profile.")
    context = {}
    if request.POST:
        # name = request.POST.get('name')
        origin = request.POST.get('my_dist')
        universityName = request.POST.get('uniname')
        # account.name = name
        account.origin = origin
        account.universityName = universityName
        account.save()
        return redirect("account:view", user_id=account.pk)
    else:

        initial = {
            "id": account.pk,
            "email": account.email,
            "name": account.name,
            "origin": account.origin,
            # 'universityName' : account.universityName,
        }

        context['form'] = initial

    return render(request, "account/edit_account.html", context)

def edit_pass_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect("login")
    user_id = kwargs.get("user_id")
    account = Account.objects.get(pk=user_id)
    if account.pk != request.user.pk:
        return HttpResponse("You cannot edit someone elses profile.")
    
    context = {}
    if request.POST:
        pass1 = request.POST.get('pass1')
        pass2 = request.POST.get('pass2')
        if pass1 != pass2:
            context['error'] = "password field and conform password field doesn't match"
            return render(request, "account/edit_account_pass.html",context)
        elif pass1 == pass2:
            account.password = make_password(pass1)
            account.save()
            context['success'] = "Password Has been Changed."
            return render(request, "account/edit_account_pass.html",context)

    
    return render(request, "account/edit_account_pass.html",context)

def tokenSend(request):
    return render(request, 'account/token_send.html')

# This is basically almost exactly the same as friends/friend_list_view
def account_search_view(request, *args, **kwargs):
    context = {}
    if request.method == "GET":
        search_query = request.GET.get("q")
        if len(search_query) > 0:
            print('The search query - ', search_query)
            # search_results = Account.objects.filter(email__icontains=search_query).filter(
            #     name__icontains=search_query).distinct()
            search_results = Account.objects.filter(email=search_query)
            print("The search results are - ",search_results)
            user = request.user
            accounts = []  # [(account1, True), (account2, False), ...]
            if user.is_authenticated:
                # get the authenticated users friend list
                auth_user_friend_list = FriendList.objects.get(user=user)
                for account in search_results:
                    accounts.append(
                        (account, auth_user_friend_list.is_mutual_friend(account)))
                context['accounts'] = accounts
            else:
                for account in search_results:
                    accounts.append((account, False))
                context['accounts'] = accounts

    return render(request, "account/search_results.html", context)


'''
Some Functions to make our life easier.
'''


def fetch_or_create_uni(name, Lat, Lon):
    try:
        university = University.objects.get(name=name)
    except University.DoesNotExist:
        university = University(name=name, lat=Lat, lon=Lon)
        university.save()

        '''
        This is a very important part of registration, here when we are creating a new university instance for the first time therefore we are also going to calculate all the universities that exist in the 60 km range of this university and add them into the nearby list -

        but the catch here is that - 

        we are all going to add this university to all the NL of universities that lies in the NL of this university
        '''
        nearby_list = []
        universities = University.objects.all()
        for uni in universities:
            Lat1 = uni.lat
            Lon1 = uni.lon

            distance = calculate_distance(Lat, Lon, Lat1, Lon1)
            if distance <= 60:
                '''
                This means that yes this uni lies with in 60 km of registration uni
                '''
                nearby_list.append(uni)

        university.nearbyList.add(*nearby_list)
        university.save()

        for uni in nearby_list:
            uni.nearbyList.add(university)
            uni.save()
        
        all_uni_profs = UniversityProfile.objects.filter(name=university.name)
        if all_uni_profs.exists():
            for prof in all_uni_profs:
                prof.delete()

    return university


def fetch_or_create_uniprofile(name, Lat, Lon, uniName):
    try:
        university = UniversityProfile.objects.get(
            Q(name=name) & Q(lat=Lat) & Q(lon=Lon))
    except UniversityProfile.DoesNotExist:
        university = UniversityProfile(
            name=name, lat=Lat, lon=Lon, universityName=uniName)
        university.save()
        nearby_list = []
        universities = University.objects.all()
        for uni in universities:
            Lat1 = uni.lat
            Lon1 = uni.lon

            distance = calculate_distance(Lat, Lon, Lat1, Lon1)
            if distance <= 60:
                '''
                This means that yes this uni lies with in 60 km of registration uni
                '''
                nearby_list.append(uni)

        university.nearbyList.add(*nearby_list)
        university.save()
    return university

#7nov12
def send_mail_after_registration(email , token):
    subject = 'Your accounts need to be verified'
    message = f'Hi paste the link to verify your account http://mystranger.in/verify/{token}'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [email]
    send_mail(subject, message , email_from ,recipient_list )

def verify(request , auth_token):
    try:
        token_obj = AccountToken.objects.filter(auth_token = auth_token).first()
        context = {}
        if token_obj:
            if token_obj.is_verified:
                # messages.success(request, 'Your account is already verified.')
                context['token_status'] = 'Your account is already verified.'
                # return redirect('login')
                return render(request, 'account/login.html',context)
            token_obj.is_verified = True
            token_obj.save()
            # messages.success(request, 'Your account has been verified.')
            context['token_status'] = 'Your account has been verified.'
            return render(request, 'account/login.html',context)
        else:
            return HttpResponse('Invalid Token')
    except Exception as e:
        print(e)
        return redirect('home')