from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from django.db.models import Q

import json

from account.models import Account
from chat.models import PrivateChatRoom, RoomChatMessage
from itertools import chain
from chat.utils import find_or_create_private_chat
from mystranger_app.models import Flags
from django.views.decorators.csrf import csrf_exempt

DEBUG = False


def private_chat_room_view(request, *args, **kwargs):
    
    user = request.user
    room_id = request.GET.get("room_id")

    context = {}

    try:


        # Redirect them if not authenticated
        if not user.is_authenticated:
            return redirect("login")

        if room_id:
            try:
                room = PrivateChatRoom.objects.get(pk=room_id)
                context["room"] = room
            except PrivateChatRoom.DoesNotExist:
                return HttpResponse('The room you are trying to access does not exist.')

        # 1. Find all the rooms this user is a part of
        rooms1 = PrivateChatRoom.objects.filter(user1=user, is_active=True)
        rooms2 = PrivateChatRoom.objects.filter(user2=user, is_active=True)

        # 2. merge the lists
        rooms = list(chain(rooms1, rooms2))
        print(str(len(rooms)))

        """
        m_and_f:
            [{"message": "hey", "friend": "Mitch"}, {
                "message": "You there?", "friend": "Blake"},]
        Where message = The most recent message
        """
        m_and_f = []
        f_and_m = []
        for room in rooms:
            # Figure out which user is the "other user" (aka friend)
            if room.user1 == user:
                friend = room.user2
            else:
                friend = room.user1

            '''
            Fetching all the unread messages send by the friend to me (in our room)
            '''

            unread_messages = RoomChatMessage.objects.filter(
                Q(room=room) & Q(user=friend) & Q(read=False))
            unread_messages_count = unread_messages.count()

            messages = RoomChatMessage.objects.filter(Q(room=room) & Q(user=friend)).order_by("-timestamp")
            message = messages.first()

            m_and_f.append({
                'unread_messages_count': unread_messages_count,
                'friend': friend,
            })

        context['m_and_f'] = m_and_f
        context['debug'] = DEBUG
        context['id'] = request.user.id
        context['debug_mode'] = settings.DEBUG
    except Exception as e:
        print(e)

    token = request.user.ntoken
    if token == 'None':
        print('the token is none bro - ', token)
    elif token == ' ':
        pass
    elif len(str(token)) > 10:
        print('the token does exist - ', token)
        context['token_exist'] = 'yes'
        
    print('token is - ', token)
    return render(request, "chat/room.html", context)

# Ajax call to return a private chatroom or create one if does not exist

@csrf_exempt
def create_or_return_private_chat(request, *args, **kwargs):
    user1 = request.user
    payload = {}
    if user1.is_authenticated:
        if request.method == "POST":
            user2_id = request.POST.get("user2_id")
            try:
                user2 = Account.objects.get(pk=user2_id, is_verified = True)
                chat = find_or_create_private_chat(user1, user2)
                payload['response'] = "Successfully got the chat."
                payload['chatroom_id'] = chat.id
            except Account.DoesNotExist:
                payload['response'] = "Unable to start a chat with that user."
    else:
        payload['response'] = "You can't start a chat if you are not authenticated."
    return HttpResponse(json.dumps(payload), content_type="application/json")


def report_view(request, *args, **kwargs):

    print('The flag view is called')
    user = request.user

    if not request.user.is_authenticated:
        return redirect("login")

    if request.POST:
        try:
            flag_user_id = request.POST.get('flag_user_id')
            flag_user_name = request.POST.get('flag_user_name')
            reason = request.POST.get('flag-reason')
            
            account = Account.objects.get(pk=flag_user_id, is_verified = True)
            
            flag_object = Flags.objects.filter(user=account, Flagger=user)
            
            if flag_object.exists():
                response_data = {
                    'status' : "Already Flagged",
                    'message' : 'You have already flagged this User!'
            }
            else:
                account.flags = account.flags + 1
                account.save()
                
                flag = Flags(flag_user_id=flag_user_id, user=account,
							reason=reason, Flagger=user)
                flag.save()
                response_data = {
                    'status' : 'Flagged',
					'message': 'This Person has been reported!'
				}

        except Exception as e:
            print('The flag exception is - ', str(e))
            response_data = {
                'status' : 'error',
                'message': str(e),
            }

    return HttpResponse(json.dumps(response_data), content_type="application/json")

