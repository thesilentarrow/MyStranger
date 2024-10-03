from django.shortcuts import render, redirect
from account.forms import RegistrationForm, AccountAuthenticationForm
from django.http import HttpResponse, HttpResponseBadRequest
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from account.models import Account
from mystranger_app.models import University, UniversityProfile , Flags
from friend.models import FriendList, FriendRequest
from django.db.models import Q
from mystranger_app.utils import calculate_distance, haversine_distance
from friend.utils import get_friend_request_or_false
from friend.friend_request_status import FriendRequestStatus
from django.contrib.auth.hashers import make_password
from mystranger.settings import accesstoken
# from CodingWithMitchChat.settings import accesstoken
import json
from django.core.mail import send_mail
import uuid
from account.models import AccountToken
from account.models import RegistrationError
from account.models import Prompt
from django.contrib import messages

from qna.models import Answer, PublicChatRoom
from django.db.models import Count
from django.db.models import F, Case, When, Value, IntegerField
from django.views.decorators.csrf import csrf_exempt



def register_view(request, *args, **kwargs):

    context = {}
    context['hide_footer'] = 'yas'
    try:
        user = request.user
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
                auth_token = str(uuid.uuid4())
                account_token = AccountToken.objects.create(user = account, auth_token = auth_token)
                account_token.save()
                send_email_view(request, email, auth_token)
                print('email has been sent!')

                notrust = request.POST.get('notrust')
                if notrust:
                    # This means that location is obtained from the user input and can't be trusted therefore we are gonna create a university profile
                    uniName = request.POST.get('universityName')
                    uniaddress = request.POST.get('universityAddress')
                    print(uniaddress)
                    university_profile = fetch_or_create_uniprofile(
                        name, lat, lon, uniName, uniaddress)
                    university_profile.add_user(account) #here we are adding our unverified user into uni profile same goes for uni model
                else:
                    '''
                    check if its true or not, so even if its not than still nothing will happen because we are not creating university models from here anyway.
                    '''
                    university = fetch_or_create_uni(name, lat, lon)
                    if university:
                        university.add_user(account)
                        nearby_universities = university.nearbyList.all()
                        for uni in nearby_universities:
                            uni.allNearbyUsers.add(account)
                            uni.save()

                
                '''
                Here we are adding the user to all_nearby_users for its nearby universities 
                '''
                
                # return HttpResponse('An email has been sent to you, please verify your account!')
                return render(request,'account/token_send.html')
                # login(request, account)
                # destination = kwargs.get('next')
                # if destination:
                #     return redirect(destination)
                # else:
                #     return redirect('home')
                # return redirect('account:token')
            else:
                context['registration_form'] = form

        else:
            form = RegistrationForm()
            context['registration_form'] = form
    except Exception as e:
        print(e)

    return render(request, 'account/register.html', context)

def tokenSend(request):
    return render(request, 'account/token_send.html')


def logout_view(request):
    logout(request)
    return redirect('home')

@csrf_exempt
def login_view(request, *args, **kwargs):

    context = {}
    context['hide_footer'] = 'yas'
    
    try:
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
                    if user_token is not None:
                        if user_token.is_verified:
                            login(request, user)
                            destination = kwargs.get('next')
                            if destination:
                                return redirect(destination)
                            else:
                                return redirect('qna:pika')
                        else:
                            messages.warning(request, 'Please Verify Your Account First!')
                            context['show_resend'] = 'yup'
                            return render(request, 'account/login.html', context)
            else:
                context['login_form'] = form
    except Exception as e:
        print(e)
        
    return render(request, 'account/login.html', context)


def resend_verif_view(request, *args, **kwargs):
  context = {}
  context['hide_footer'] = 'yas'

  if request.method == 'POST':
    try:

      email = request.POST.get('email')

      try:
          user = Account.objects.filter(email=email).first()
          token_obj = AccountToken.objects.filter(user=user).first()
          token = token_obj.auth_token
          subject = 'Your account needs to be verified'
          html_message = verif_email_content(token)
          message = f'Hi paste the link to verify your account https://mystranger.in/account/verify/{token}'
          from_email = 'info@mystranger.in'
          recipient_list = [email]
          send_mail(subject, message, from_email, recipient_list, html_message=html_message)
          context['email_sent'] = 'verification email has been sent to your email, you can verify your account by clicking on the verification link. it can take upto 1 - 2 mins for the mail to reach you  '
      except Exception as e:
          print('The resend verif exception  - ', str(e))

      
      
    except Exception as e:
        print('unable to send email - ', str(e))
      

  return render(request, 'account/resend_verif.html', context)
    

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
    if str(request.user.id) == str(user_id): 
      context['is_active'] = 'account'
    # print('req', type(request.user.id),type(user_id))
    try:
        account = Account.objects.get(pk=user_id, is_verified = True)
        print('why is it showing md there - ',account)
    except:
        return HttpResponse("Account Does Not Exist! or Is not verified Yet!")
    
    if request.user.is_authenticated:
        userva = request.user
        userva.update_last_activity()

    if account:
        context['id'] = account.id
        context['name'] = account.name
        context['email'] = account.email
        context['origin'] = account.origin
        context['account'] = account
        # print('the fuckin account name - ',account)
        if account.bio:
          context['bio'] = account.bio
        # context['universityName'] = account.universityName
        try:
          # my_answers_count = Answer.objects.filter(user=account, parent = None).count()
          # print(my_answers_count,'the fuckin anus count')
          # print('The asception was here -')
          
          # my_answers_recieved_count = 0
          # questions = PublicChatRoom.objects.filter(owner=account)
          # for question in questions:
          #     # my_answers_recieved_count += question.answers.filter(parent=None).count()
          #     my_answers_recieved_count +=  Answer.objects.filter(question=question, parent=None).count()

              # print(my_answers_recieved_count)

          # print('The asception was here or here -')
            
          # all the posts this person has vibed on
          # questions = PublicChatRoom.objects.all()
          # my_vibe_count = 0
          # for question in questions:
          #   for poll in question.polls.all():
          #     if request.user in poll.polled.all():
          #         my_vibe_count += 1

          # all_vibes = my_vibe_count
          # print('these are the no. of vibes i did - ', all_vibes)

          # context['vibe_score'] = my_answers_count + my_answers_recieved_count + all_vibes
              
          # now vibe score is the no. of vibes a person received on its post + all the comments/replies she received on its post
          questions = PublicChatRoom.objects.filter(owner=account)

          my_vibe_count = 0
          if questions.exists():
            for question in questions:
                my_vibe_count += question.poll_count() + question.answers.all().count()
            
          context['vibe_score'] = my_vibe_count

          print('The fuckin wibe score - ', context['vibe_score'])
          
        except Exception as e:
            print('Exception at account view - ', str(e))

        context['gender'] = account.gender

        email = account.email
        email_part , dom_part = email.split('@')
        hidden_email = email_part[:3] + ''
        # print(hidden_email)
        for i in email_part[3:]:
            hidden_email += '*'
            # print(i)
        hidden_email = hidden_email + '@' + dom_part
        context['hidden_email'] = hidden_email

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

        if is_self:

          try:
              university = University.objects.get(name=request.user.university_name)
              nearby_list_count = university.nearbyList.all().count()
              context['nearby_list_count'] = nearby_list_count
          except University.DoesNotExist:
              university = UniversityProfile.objects.get(name=request.user.university_name)
              nearby_list_count = university.nearbyList.all().count()
              context['nearby_list_count'] = nearby_list_count

        show = request.GET.get('show')
        print('This is show -', show)

        prompts = Prompt.objects.filter(user=account)
        if prompts:
          context['show_btn'] = 'showi'

        
        if show == 'realme':
      
          prompts = Prompt.objects.filter(user=account)

          context['realme'] = 'ouy hoey'
          if prompts:
            #check whether the user has propts of or not
            context['prompts'] = prompts
        

        elif (show == 'vibes'):

          '''
          Now we wanna show all the questions that this user has either hunched on or had answered
          '''

          question_answers = [] # ['{question' : {answers}}]

          # here we wanna fetch those questions which this user (we are looking at had polled or answered at)
          questions = PublicChatRoom.objects.all().order_by('-timestamp')

          # # questions = PublicChatRoom.objects.all().exclude(answers__user = request.user)
          questions = questions.order_by('-timestamp')
          

          for question in questions:
              # question_answers.append([question, question.answers.all()])
              # print('question - ', question)

              skip_loop_due_answer = False
              if not question.answers.filter(user=account, parent=None).exists():
                  skip_loop_due_answer = True

              '''
              check if the question is not already polled than don't show it to the user + if he/she hasn't answered that too
              '''
              skip_outer_loop = False
              
              for poll in question.polls.all():
                  if account in poll.polled.all():
                      # This means the user has not polled this ques now check whether he has answered it
                      skip_outer_loop = True
                      

              
              if (not skip_outer_loop) and skip_loop_due_answer:
                  continue  # skip the remaining iterations of the outer loop
              

              poll_status = question.is_already_polled(request.user)
              answers_with_descendants = []

              # Now this is not going to be the top answer , the top answer is going to be the one that this user has answered
              answers = question.answers.filter(parent=None,user=account).annotate(report_count=Count('ans_reports')).exclude(report_count__gt=10)
              answers = answers.order_by('-timestamp')[:1]

              

              top2_ans = []
              for answer in answers:
                  # print('The parent answer - ', answer)
                  
                  answers_and_replies = [answer] + list(answer.get_descendants())
                  answers_with_descendants.extend(answers_and_replies) 
                  top2_ans.append(answer.pk)
              
              # assuming that above instead of sending the first 2 answers we have send the top 2 answers , now we want to send the rest of the answers excluding the above 2

              other_answers_with_descendants = []

              if not question.polls.all():
                  answers = question.answers.filter(parent=None).exclude(id__in=top2_ans)
              else:
                  answers = question.answers.filter(parent=None)
              
              
              answers = answers.order_by('-timestamp')
              answers = answers.annotate(
              is_axce=Case(
                  When(user=account, then=Value(1)),
                  default=Value(0),
                  output_field=IntegerField(),
              )
          )
              answers = answers.order_by('-is_axce', '-timestamp')

              for answer in answers:
                  # print('This is what the pending answers are - ', answer)
                  # print('The answer - ',answer,' The reports - ',answer.ans_reports.all().count())
                  if answer.ans_reports.all().count() < 5:
                      other_answers_and_replies = [answer] + list(answer.get_descendants())
                      other_answers_with_descendants.extend(other_answers_and_replies) 
              


              
              question_answers.append([question,answers_with_descendants, other_answers_with_descendants, poll_status])
                  
              
        
          context['question_top2_answers'] = question_answers
          context['answers_active'] = 'yup'
        
        else:

          print('Broooo wanted to seee the posts section in account')

          # show all the posts this user account has posted

          question_answers = [] # ['{question' : {answers}}]

          # here we wanna fetch those questions which this user (we are looking at had polled or answered at)
          questions = PublicChatRoom.objects.filter(owner=account)

          # # questions = PublicChatRoom.objects.all().exclude(answers__user = request.user)
          questions = questions.order_by('-timestamp')
          

          for question in questions:
              # question_answers.append([question, question.answers.all()])
              # print('question - ', question)

              skip_loop_due_answer = False
              if not question.answers.filter(user=account, parent=None).exists():
                  skip_loop_due_answer = True

              '''
              check if the question is not already polled than don't show it to the user + if he/she hasn't answered that too
              '''
              skip_outer_loop = False
              
              for poll in question.polls.all():
                  if account in poll.polled.all():
                      # This means the user has not polled this ques now check whether he has answered it
                      skip_outer_loop = True
                      

              
              # if (not skip_outer_loop) and skip_loop_due_answer:
              #     continue  # skip the remaining iterations of the outer loop
              

              poll_status = question.is_already_polled(request.user)
              answers_with_descendants = []

              # Now this is not going to be the top answer , the top answer is going to be the one that this user has answered
              answers = question.answers.filter(parent=None,user=account).annotate(report_count=Count('ans_reports')).exclude(report_count__gt=10)
              answers = answers.order_by('-timestamp')[:1]

              if not answers:
                  answers = question.answers.filter(parent=None).annotate(report_count=Count('ans_reports')).exclude(report_count__gt=10)
                  answers = answers.annotate(num_likes=Count('likes'))
                  answers = answers.order_by('-num_likes')[:1]

              

              top2_ans = []
              for answer in answers:
                  # print('The parent answer - ', answer)
                  
                  answers_and_replies = [answer] + list(answer.get_descendants())
                  answers_with_descendants.extend(answers_and_replies) 
                  top2_ans.append(answer.pk)
              
              # assuming that above instead of sending the first 2 answers we have send the top 2 answers , now we want to send the rest of the answers excluding the above 2

              other_answers_with_descendants = []

              if not question.polls.all():
                  answers = question.answers.filter(parent=None).exclude(id__in=top2_ans)
              else:
                  answers = question.answers.filter(parent=None)
              
              
              answers = answers.order_by('-timestamp')
              answers = answers.annotate(
              is_axce=Case(
                  When(user=account, then=Value(1)),
                  default=Value(0),
                  output_field=IntegerField(),
              )
          )
              answers = answers.order_by('-is_axce', '-timestamp')

              for answer in answers:
                  # print('This is what the pending answers are - ', answer)
                  # print('The answer - ',answer,' The reports - ',answer.ans_reports.all().count())
                  if answer.ans_reports.all().count() < 5:
                      other_answers_and_replies = [answer] + list(answer.get_descendants())
                      other_answers_with_descendants.extend(other_answers_and_replies) 
              


              
              question_answers.append([question,answers_with_descendants, other_answers_with_descendants, poll_status])
                  
              
        
          context['question_top2_answers'] = question_answers
          context['posts_active'] = 'yes'

        
        
            


        return render(request, "account/account.html", context)


def edit_account_view(request, *args, **kwargs):
    try:

        if not request.user.is_authenticated:
            return redirect("login")
        user_id = kwargs.get("user_id")
        account = Account.objects.get(pk=user_id, is_verified = True)
        if account.pk != request.user.pk:
            return HttpResponse("You cannot edit someone elses profile.")
        context = {}
        if request.POST:
            # name = request.POST.get('name')
            origin = request.POST.get('my_dist')
            bio = request.POST.get('bio')
            # print('This is the bio - ', bio)
            # account.name = name
            account.bio = bio
            account.origin = origin
            # account.universityName = universityName
            account.save()
            return redirect("account:view", user_id=account.pk)
        else:
            name = account.university_name
            try:
                uni = University.objects.get(name = name)
                uni_name = uni.universityName
            except University.DoesNotExist:
                uni = UniversityProfile.objects.get(name= name)
                uni_name = uni.universityName

            email = account.email
            domain = email.split('@')[-1:][0]
            initial = {
                "id": account.pk,
                "email": account.email,
                "name": account.name,
                "origin": account.origin,
                'bio':account.bio,
                'universityName' : uni_name,
                'domain' : domain,
            }

            

            context['form'] = initial

    except Exception as e:
        print(e)
        
    return render(request, "account/edit_account.html", context)

# def edit_pass_view(request, *args, **kwargs):
#     if not request.user.is_authenticated:
#         return redirect("login")
#     user_id = kwargs.get("user_id")
#     account = Account.objects.get(pk=user_id)
#     if account.pk != request.user.pk:
#         return HttpResponse("You cannot edit someone elses profile.")
    
#     context = {}
#     if request.POST:
#         pass1 = request.POST.get('pass1')
#         pass2 = request.POST.get('pass2')
#         if pass1 != pass2:
#             context['error'] = "password field and conform password field doesn't match"
#             return render(request, "account/edit_account_pass.html",context)
#         elif pass1 == pass2:
#             account.password = make_password(pass1)
#             account.save()
#             context['success'] = "Password Has been Changed."
#             return render(request, "account/edit_account_pass.html",context)

    
#     return render(request, "account/edit_account_pass.html",context)

def prompt_view(request, *args, **kwargs):
    
    if request.method == 'POST':

      if request.POST.get('action') == 'delete':
          print('a prompt delete req came')

          id = request.POST.get('promp-id')
          try:
                promptva = Prompt.objects.get(pk=id)
                print('This prompt is getting deleted - ', promptva)

                if promptva.user == request.user:
                    promptva.delete()

                response_data = {
                'status' : 'delete done',
                'response' : 'card deleted',
            }
          except Exception as e:
              print('error fetching the prompt')
              response_data = {
              'status' : 'error',
              'message': str(e),
          }
              
          return HttpResponse(json.dumps(response_data), content_type="application/json")
          

      if 'main-prompt-id' in request.POST:
          print('Main-prompt is submitted')

          question = request.POST.get('selectedQuestion')
          answer = request.POST.get('prompt-answer')
          
  
          if question and answer:
              print(question,answer)

              '''
              Now before creating a prompt we wanna check how many prompts does this user have
              if it's less than 5 than cool else redirect the user to his/her prompts and tell to delete some
              '''

              # checking his total prompts

              prompts = Prompt.objects.filter(user=request.user)
              if len(prompts)>=5:
                  messages.warning(request, 'you can only add 5 prompts, delete some of your old prompts to add a new one. ')
                  return redirect("account:view", user_id=request.user.pk)
                  # return HttpResponse('You can only add one prompt at max bitch')
              else:
                # adding a prompt
                promptva = Prompt(user=request.user, question=question, answer=answer)
                promptva.save()

                return redirect("account:view", user_id=request.user.pk)
          # else:
          #     messages.warning(request, 'Please add atleast two poles or add none...')
          #     return redirect("account:view", user_id=request.user.pk)
      if 'custom-prompt-id' in request.POST:
          print('Main-prompt is submitted')

          question = request.POST.get('custom-question')
          answer = request.POST.get('custom-prompt-answer')
          
  
          if question and answer:
              print(question,answer)

              '''
              Now before creating a prompt we wanna check how many prompts does this user have
              if it's less than 5 than cool else redirect the user to his/her prompts and tell to delete some
              '''

              # checking his total prompts

              prompts = Prompt.objects.filter(user=request.user)
              if len(prompts)>=5:
                  messages.warning(request, 'you can only add 5 prompts, delete some of your old prompts to add a new one. ')
                  return redirect("account:view", user_id=request.user.pk)
                  # return HttpResponse('You can only add one prompt at max bitch')
              else:
                # adding a prompt
                promptva = Prompt(user=request.user, question=question, answer=answer)
                promptva.save()

                return redirect("account:view", user_id=request.user.pk)

            



    return render(request, 'account/prompt_edit.html')


# This is basically almost exactly the same as friends/friend_list_view
def account_search_view(request, *args, **kwargs):
    context = {}
    try:

        if request.method == "GET":
            search_query = request.GET.get("q")
            if len(search_query) > 0:
                print('The search query - ', search_query)
                search_results = Account.objects.filter(Q(name__icontains=search_query) & Q(is_verified = True) )
                # search_results = Account.objects.filter(email=search_query, is_verified = True)
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

    except Exception as e:
        print(e)

    return render(request, "account/search_results.html", context)


'''
Some Functions to make our life easier.
'''


def fetch_or_create_uni(name, Lat, Lon):
    try:
        university = University.objects.get(name=name)
        return university

        # nearby_unis = university.nearbyList.all()
        # all_nearby_users = []
        # for uni in nearby_unis:
        #    uni.allNearbyUsers.add(account)

        # university.allNearbyUsers.add(*all_nearby_users)
        # university.save()
    except University.DoesNotExist:
        print('Request university does not exist')
        # university = University(name=name, lat=Lat, lon=Lon)
        # university.save()

        # '''
        # This is a very important part of registration, here when we are creating a new university instance for the first time therefore we are also going to calculate all the universities that exist in the 60 km range of this university and add them into the nearby list -

        # but the catch here is that - 

        # we are all going to add this university to all the NL of universities that lies in the NL of this university
        # '''
        # nearby_list = []
        # universities = University.objects.all()
        # for uni in universities:
        #     Lat1 = uni.lat
        #     Lon1 = uni.lon

        #     # distance = calculate_distance(Lat, Lon, Lat1, Lon1)
        #     distance = haversine_distance(Lat, Lon, Lat1, Lon1)
        #     if distance <= 60:
        #         '''
        #         This means that yes this uni lies with in 60 km of registration uni
        #         '''
        #         nearby_list.append(uni)

        # university.nearbyList.add(*nearby_list)
        # university.save()

        # for uni in nearby_list:
        #     uni.nearbyList.add(university)
        #     uni.save()
        
        # all_uni_profs = UniversityProfile.objects.filter(name=university.name)
        # if all_uni_profs.exists():
        #     for prof in all_uni_profs:
        #         prof.delete()

    


def fetch_or_create_uniprofile(name, Lat, Lon, uniName, uniaddress):
    try:
        university = UniversityProfile.objects.get(
            Q(name=name) & Q(lat=Lat) & Q(lon=Lon))
    except UniversityProfile.DoesNotExist:
        university = UniversityProfile(
            name=name, lat=Lat, lon=Lon, universityName=uniName, universityAddress = uniaddress)
        university.save()

        ''' idiot we do need this to make site work for patient zero '''


        nearby_list = []
        all_nearby_users = []
        universities = University.objects.all()
        for uni in universities:
            Lat1 = uni.lat
            Lon1 = uni.lon
            
        #     # distance = calculate_distance(Lat, Lon, Lat1, Lon1)
        #     # if distance:
        #     #     if distance <= 60:
        #     #         '''
        #     #         This means that yes this uni lies with in 60 km of registration uni
        #     #         '''
        #     #         nearby_list.append(uni)
        #     # else:
            distance = haversine_distance(float(Lat), float(Lon), float(Lat1), float(Lon1))
            if distance <= 60:
                '''
                This means that yes this uni lies with in 60 km of registration uni
                '''
                nearby_list.append(uni)

                '''
                This part can be done asyncronously because its not needed instantly , it can be done later.
                '''

                # print(uni.users.all())
                # print(type(uni.users.all()))
                uni_users = uni.users.all()
                # print("users from - ",uni)
                if uni_users:
                    for usr in uni_users:
                        all_nearby_users.append(usr)

        university.nearbyList.add(*nearby_list)
        university.allNearbyUsers.add(*all_nearby_users)
        # print('allnearby users - ', all_nearby_users)
        university.save()
    return university


def send_email_view(request, email, token):
    try:

        subject = 'Your account needs to be verified'
        html_message = verif_email_content(token)
        message = f'Hi paste the link to verify your account http://mystranger.in/account/verify/{token}'
        from_email = 'MyStrangerTeam@mystranger.in'
        recipient_list = [email]
        send_mail(subject, message, from_email, recipient_list, html_message=html_message)
        
    except Exception as e:
        print('unable to send email - ', str(e))
        
    # email_from = settings.EMAIL_HOST_USER
    # recipient_list = [email]
    # send_mail(subject, message , email_from ,recipient_list )

def verify(request , auth_token):
    try:
        token_obj = AccountToken.objects.filter(auth_token = auth_token).first()
        context = {}
        if token_obj:
            if token_obj.is_verified:
                messages.success(request, 'Your account is already verified.')
                return redirect('login')
                
            token_obj.user.is_verified = True
            token_obj.user.save()  
            token_obj.is_verified = True
            token_obj.save()
            messages.success(request, 'Your account has been verified.')
            return redirect('login')
            
        else:
            return HttpResponse('Invalid Token')
    except Exception as e:
        print(e)
        return redirect('home')

def nearby_uni(request):
    context = {}
    try:
        if not request.user.is_authenticated:
            return redirect("login")
        
        user = request.user
        user_university_name = user.university_name
        nearby_lst = []
        try:
            uni_obj = University.objects.get(name=user_university_name)
            user_uni_num = uni_obj.users.filter(is_verified = True).count()
            context['user_uni'] = uni_obj.universityName
            context['user_uni_domain'] = uni_obj.name
            context['user_uni_num'] = user_uni_num
            context['user_uni_id'] = uni_obj.id

            nearby_universities = uni_obj.nearbyList.all()
            for university in nearby_universities:
                # print(university)
                # print(type(university))
                if not university.name == user_university_name:
                    nearby_lst.append({
                        'university' : university.universityName,
                        'students' : university.users.filter(is_verified = True).count(),
                        'domain' : university.name,
                        'uni_id' : university.id
                    })
            context['nearby_lst'] = nearby_lst
            # print(nearby_lst)


        except University.DoesNotExist:
            try:
                uni_prof = UniversityProfile.objects.get(name=user_university_name)
                user_uni_num = uni_obj.users.filter(is_verified = True).count()
                context['user_uni'] = uni_obj.universityName
                context['user_uni_num'] = user_uni_num
                context['user_uni_id'] = uni_obj.id

                nearby_universities = uni_obj.nearbyList.all()
                for university in nearby_universities:
                    if not university.name == user_university_name:
                        nearby_lst.append({
                            'university' : university.universityName,
                            'students' : university.users.filter(is_verified = True).count(),
                            'domain' : university.name,
                            'uni_id' : university.id

                        })
                context['nearby_lst'] = nearby_lst
                
            except UniversityProfile.DoesNotExist:
                print('Something Went Wrong....')
        
    except Exception as e:
        print(e)
    return render(request, 'account/nearby_uni_list.html',context)



def nearby_uni_stud(request,  *args, **kwargs):
    context = {}
    try:
        if not request.user.is_authenticated:
            return redirect("login")
        
        uni_id = kwargs.get('uni_id')

        try:
            uni_obj = University.objects.get(id=uni_id)
        except University.DoesNotExist:
            return HttpResponse('The university you are looking for does not exist!')
        
        if uni_obj:
            user_uni_num = uni_obj.users.filter(is_verified = True).count()
            context['user_uni'] = uni_obj.universityName
            context['user_uni_domain'] = uni_obj.name
            context['user_uni_num'] = user_uni_num

            uni_students = uni_obj.users.filter(is_verified=True)
            nearby_lst = []
            for student in uni_students:
                # print(university)
                # print(type(university))

                account = request.user
                auth_user_friend_list = FriendList.objects.get(user=account)

                if student.bio:
                    bio = student.bio
                else: 
                    bio = ""
               
                nearby_lst.append({
                    'name' : student.name,
                    'id' : student.id,
                    'bio' : bio,
                    'is_friend' : auth_user_friend_list.is_mutual_friend(student),
                })
            context['nearby_lst'] = nearby_lst
        
       
        
    except Exception as e:
        print(e)
    return render(request, 'account/nearby_uni_stud_list.html',context)

def registration_error(request):
    context = {}
    if request.method=='POST':
        user_email = request.POST.get('user-email')
        user_university = request.POST.get('userUniversityName')
        user_university_address = request.POST.get('userUniversityAddress')
        issue_faced = request.POST.get('issue-message')

        reg_error_obj = RegistrationError(email = user_email, uni_name = user_university, uni_address = user_university_address, issue_faced = issue_faced)
        reg_error_obj.save()
        context['success'] = 'Success'
        return render(request, 'account/registration_error_form.html', context)
        
    return render(request, 'account/registration_error_form.html', context)

def add_user_to_allnearbyusers(user):
    return

def verif_email_content(token):

    
    stringi = f"""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">

<head>
  <!--[if gte mso 9]>
<xml>
  <o:OfficeDocumentSettings>
    <o:AllowPNG/>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings>
</xml>
<![endif]-->
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="x-apple-disable-message-reformatting">
  <!--[if !mso]><!-->
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <!--<![endif]-->
  <title></title>

  <style type="text/css">
    
  </style>



  <!--[if !mso]><!-->
  <link href="https://fonts.googleapis.com/css?family=Cabin:400,700" rel="stylesheet" type="text/css">
  <!--<![endif]-->

</head>

<body class="clean-body u_body" style="margin: 0;padding: 0;-webkit-text-size-adjust: 100%;background-color: #f9f9f9;color: #000000">
  <!--[if IE]><div class="ie-container"><![endif]-->
  <!--[if mso]><div class="mso-container"><![endif]-->
  <table id="u_body" style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;min-width: 320px;Margin: 0 auto;background-color: #f9f9f9;width:100%" cellpadding="0" cellspacing="0">
    <tbody>
      <tr style="vertical-align: top">
        <td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top">
          <!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color: #f9f9f9;"><![endif]-->



          <div class="u-row-container" style="padding: 0px;background-color: transparent">
            <div class="u-row" style="margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;">
              <div style="border-collapse: collapse;display: table;width: 100%;height: 100%;background-color: transparent;">
                <!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]-->

                <!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]-->
                <div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;">
                  <div style="height: 100%;width: 100% !important;">
                    <!--[if (!mso)&(!IE)]><!-->
                    <div style="box-sizing: border-box; height: 100%; padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;">
                      <!--<![endif]-->

                      <table style="font-family:'Cabin',sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                        <tbody>
                          <tr>
                            <td style="overflow-wrap:break-word;word-break:break-word;padding:20px;font-family:'Cabin',sans-serif;" align="left">

                              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                  <td style="padding-right: 0px;padding-left: 0px;" align="center">

                                    

                                  </td>
                                </tr>
                              </table>

                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <!--[if (!mso)&(!IE)]><!-->
                    </div>
                    <!--<![endif]-->
                  </div>
                </div>
                <!--[if (mso)|(IE)]></td><![endif]-->
                <!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]-->
              </div>
            </div>
          </div>





          <div class="u-row-container" style="padding: 0px;background-color: transparent">
            <div class="u-row" style="margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #003399;">
              <div style="border-collapse: collapse;display: table;width: 100%;height: 100%;background-color: transparent;">
                <!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #003399;"><![endif]-->

                <!--[if (mso)|(IE)]><td align="center" width="600" style="background-color: #009cda;width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]-->
                <div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;">
                  <div style="background-color: #009cda;height: 100%;width: 100% !important;">
                    <!--[if (!mso)&(!IE)]><!-->
                    <div style="box-sizing: border-box; height: 100%; padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;">
                      <!--<![endif]-->

                      <table style="font-family:'Cabin',sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                        <tbody>
                          <tr>
                            <td style="overflow-wrap:break-word;word-break:break-word;padding:40px 10px 10px;font-family:'Cabin',sans-serif;" align="left">

                              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                  <td style="padding-right: 0px;padding-left: 0px;" align="center">

                                    

                                  </td>
                                </tr>
                              </table>

                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <table style="font-family:'Cabin',sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                        <tbody>
                          <tr>
                            <td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:'Cabin',sans-serif;" align="left">

                              <div style="font-size: 14px; color: #ffffff; line-height: 140%; text-align: center; word-wrap: break-word;">
                                <p style="font-size: 14px; line-height: 140%;"><strong>T H A N K S&nbsp; &nbsp;F O R&nbsp; &nbsp;S I G N I N G&nbsp; &nbsp;U P !</strong></p>
                              </div>

                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <table style="font-family:'Cabin',sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                        <tbody>
                          <tr>
                            <td style="overflow-wrap:break-word;word-break:break-word;padding:0px 10px 31px;font-family:'Cabin',sans-serif;" align="left">

                              <div style="font-size: 14px; color: #ffffff; line-height: 140%; text-align: center; word-wrap: break-word;">
                                <p style="font-size: 14px; line-height: 140%;"><span style="font-size: 28px; line-height: 39.2px;"><strong><span style="line-height: 39.2px; font-size: 28px;">Verify Your E-mail Address </span></strong>
                                  </span>
                                </p>
                              </div>

                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <!--[if (!mso)&(!IE)]><!-->
                    </div>
                    <!--<![endif]-->
                  </div>
                </div>
                <!--[if (mso)|(IE)]></td><![endif]-->
                <!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]-->
              </div>
            </div>
          </div>





          <div class="u-row-container" style="padding: 0px;background-color: transparent">
            <div class="u-row" style="margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;">
              <div style="border-collapse: collapse;display: table;width: 100%;height: 100%;background-color: transparent;">
                <!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]-->

                <!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]-->
                <div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;">
                  <div style="height: 100%;width: 100% !important;">
                    <!--[if (!mso)&(!IE)]><!-->
                    <div style="box-sizing: border-box; height: 100%; padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;">
                      <!--<![endif]-->

                      <table style="font-family:'Cabin',sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                        <tbody>
                          <tr>
                            <td style="overflow-wrap:break-word;word-break:break-word;padding:33px 55px;font-family:'Cabin',sans-serif;" align="left">

                              <div style="font-size: 14px; line-height: 160%; text-align: center; word-wrap: break-word;">
                                <p style="font-size: 14px; line-height: 160%;"><span style="font-size: 22px; line-height: 35.2px;">Hi, </span></p>
                                <p style="font-size: 14px; line-height: 160%;"><span style="font-size: 18px; line-height: 28.8px;">You're almost ready to get started. Please click on the button below to verify your email address and enjoy exclusive college experience with us! </span></p>
                              </div>

                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <table style="font-family:'Cabin',sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                        <tbody>
                          <tr>
                            <td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:'Cabin',sans-serif;" align="left">

                              <!--[if mso]><style>.v-button </style><![endif]-->
                              <div align="center">
                                <!--[if mso]><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="https://mystranger.in/account/verify/token" style="height:46px; v-text-anchor:middle; width:235px;" arcsize="8.5%"  stroke="f" fillcolor="#ff6600"><w:anchorlock/><center style="color:#FFFFFF;"><![endif]-->
                                <a href="https://mystranger.in/account/verify/{token}" target="_blank" class="v-button" style="box-sizing: border-box;display: inline-block;text-decoration: none;-webkit-text-size-adjust: none;text-align: center;color: #FFFFFF; background-color: #ff6600; border-radius: 4px;-webkit-border-radius: 4px; -moz-border-radius: 4px; width:auto; max-width:100%; overflow-wrap: break-word; word-break: break-word; word-wrap:break-word; mso-border-alt: none;font-size: 14px;">
                                  <span style="display:block;padding:14px 44px 13px;line-height:120%;"><span style="font-size: 16px; line-height: 19.2px;"><strong><span style="line-height: 19.2px; font-size: 16px;">VERIFY YOUR EMAIL</span></strong>
                                  </span>
                                  </span>
                                </a>
                                <!--[if mso]></center></v:roundrect><![endif]-->
                              </div>

                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <table style="font-family:'Cabin',sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                        <tbody>
                          <tr>
                            <td style="overflow-wrap:break-word;word-break:break-word;padding:33px 55px 60px;font-family:'Cabin',sans-serif;" align="left">

                              <div style="font-size: 14px; line-height: 160%; text-align: center; word-wrap: break-word;">
                                <p style="line-height: 160%; font-size: 14px;"><span style="font-size: 18px; line-height: 28.8px;">Thanks,</span></p>
                                <p style="line-height: 160%; font-size: 14px;"><a target="_blank" href="https://mystranger.in/" rel="noopener"><span style="font-size: 16px; line-height: 25.6px;">MyStranger.in</span></a></p>
                              </div>

                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <!--[if (!mso)&(!IE)]><!-->
                    </div>
                    <!--<![endif]-->
                  </div>
                </div>
                <!--[if (mso)|(IE)]></td><![endif]-->
                <!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]-->
              </div>
            </div>
          </div>





          <div class="u-row-container" style="padding: 0px;background-color: transparent">
            <div class="u-row" style="margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #e5eaf5;">
              <div style="border-collapse: collapse;display: table;width: 100%;height: 100%;background-color: transparent;">
                <!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #e5eaf5;"><![endif]-->

                <!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]-->
                <div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;">
                  <div style="height: 100%;width: 100% !important;">
                    <!--[if (!mso)&(!IE)]><!-->
                    <div style="box-sizing: border-box; height: 100%; padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;">
                      <!--<![endif]-->

                      <table style="font-family:'Cabin',sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                        <tbody>
                          <tr>
                            <td style="overflow-wrap:break-word;word-break:break-word;padding:41px 55px 18px;font-family:'Cabin',sans-serif;" align="left">

                              <div style="font-size: 14px; color: #003399; line-height: 160%; text-align: center; word-wrap: break-word;">
                                <p style="font-size: 14px; line-height: 160%;"><span style="font-size: 20px; line-height: 32px;"><strong>Get in touch</strong></span></p>
                                <p style="font-size: 14px; line-height: 160%;"><span style="font-size: 16px; line-height: 25.6px; color: #000000;">Info@mystranger.in</span></p>
                              </div>

                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <table style="font-family:'Cabin',sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                        <tbody>
                          <tr>
                            <td style="overflow-wrap:break-word;word-break:break-word;padding:10px 10px 33px;font-family:'Cabin',sans-serif;" align="left">

                              <div align="center">
                                <div style="display: table; max-width:146px;">
                                  <!--[if (mso)|(IE)]><table width="146" cellpadding="0" cellspacing="0" border="0"><tr><td style="border-collapse:collapse;" align="center"><table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; mso-table-lspace: 0pt;mso-table-rspace: 0pt; width:146px;"><tr><![endif]-->


                                  <!--[if (mso)|(IE)]><td width="32" style="width:32px; padding-right: 17px;" valign="top"><![endif]-->
                                  <table align="left" border="0" cellspacing="0" cellpadding="0" width="32" height="32" style="width: 32px !important;height: 32px !important;display: inline-block;border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;margin-right: 17px">
                                    <tbody>
                                      <tr style="vertical-align: top">
                                        <td align="left" valign="middle" style="word-break: break-word;border-collapse: collapse !important;vertical-align: top">
                                         
                                        </td>
                                      </tr>
                                    </tbody>
                                  </table>
                                  <!--[if (mso)|(IE)]></td><![endif]-->

                                  <!--[if (mso)|(IE)]><td width="32" style="width:32px; padding-right: 17px;" valign="top"><![endif]-->
                                  <table align="left" border="0" cellspacing="0" cellpadding="0" width="32" height="32" style="width: 32px !important;height: 32px !important;display: inline-block;border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;margin-right: 17px">
                                    <tbody>
                                      <tr style="vertical-align: top">
                                        <td align="left" valign="middle" style="word-break: break-word;border-collapse: collapse !important;vertical-align: top">
                                         
                                        </td>
                                      </tr>
                                    </tbody>
                                  </table>
                                  <!--[if (mso)|(IE)]></td><![endif]-->

                                  <!--[if (mso)|(IE)]><td width="32" style="width:32px; padding-right: 0px;" valign="top"><![endif]-->
                                  <table align="left" border="0" cellspacing="0" cellpadding="0" width="32" height="32" style="width: 32px !important;height: 32px !important;display: inline-block;border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;margin-right: 0px">
                                    <tbody>
                                      <tr style="vertical-align: top">
                                        <td align="left" valign="middle" style="word-break: break-word;border-collapse: collapse !important;vertical-align: top">
                                          
                                        </td>
                                      </tr>
                                    </tbody>
                                  </table>
                                  <!--[if (mso)|(IE)]></td><![endif]-->


                                  <!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]-->
                                </div>
                              </div>

                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <!--[if (!mso)&(!IE)]><!-->
                    </div>
                    <!--<![endif]-->
                  </div>
                </div>
                <!--[if (mso)|(IE)]></td><![endif]-->
                <!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]-->
              </div>
            </div>
          </div>





          <div class="u-row-container" style="padding: 0px;background-color: transparent">
            <div class="u-row" style="margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #003399;">
              <div style="border-collapse: collapse;display: table;width: 100%;height: 100%;background-color: transparent;">
                <!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #003399;"><![endif]-->

                <!--[if (mso)|(IE)]><td align="center" width="600" style="background-color: #009cda;width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]-->
                <div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;">
                  <div style="background-color: #009cda;height: 100%;width: 100% !important;">
                    <!--[if (!mso)&(!IE)]><!-->
                    <div style="box-sizing: border-box; height: 100%; padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;">
                      <!--<![endif]-->

                      <table style="font-family:'Cabin',sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                        <tbody>
                          <tr>
                            <td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:'Cabin',sans-serif;" align="left">

                              <div style="font-size: 14px; color: #ffffff; line-height: 180%; text-align: center; word-wrap: break-word;">
                                <p style="font-size: 14px; color: #ffffff; line-height: 180%;"><span style="font-size: 16px; color: #ffffff; line-height: 28.8px;">Copyrights © mystranger.in All Rights Reserved</span></p>
                              </div>

                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <!--[if (!mso)&(!IE)]><!-->
                    </div>
                    <!--<![endif]-->
                  </div>
                </div>
                <!--[if (mso)|(IE)]></td><![endif]-->
                <!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]-->
              </div>
            </div>
          </div>



          <!--[if (mso)|(IE)]></td></tr></table><![endif]-->
        </td>
      </tr>
    </tbody>
  </table>
  <!--[if mso]></div><![endif]-->
  <!--[if IE]></div><![endif]-->
</body>

</html>
"""
    return stringi