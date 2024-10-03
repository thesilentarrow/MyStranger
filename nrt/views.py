from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from django.db.models import Q

import json

from account.models import Account
# from chat.models import PrivateChatRoom, RoomChatMessage
from itertools import chain
from chat.utils import find_or_create_private_chat
from mystranger_app.models import Flags

from nrt.models import NrtPrivateChatRoom, NrtRoomChatMessage, AllActivatedUsers, Meetup, MeetupConnection, NrtIceBreakers
from mystranger_app.models import University
from django.utils import timezone
from datetime import timedelta
import random


DEBUG = False


def nrt_text_wow_view(request, *args, **kwargs):
    return render(request, 'nrt/newf.html')


def nrt_text_how_view(request, *args, **kwargs):
    return render(request, 'nrt/nrt_text_how.html')

def nrt_text_view(request, *args, **kwargs):
    
    context = {}
    context['is_active'] = 'nrt'
    user = request.user

    if request.user.is_authenticated:
        user.update_last_activity()

    # if request.user.email == 'himanshu.20scse1010431@galgotiasuniversity.edu.in':

    # here we are also gonna delete all the rooms whose lifetime is gt 24 hrs
    threshold = timezone.now() - timezone.timedelta(hours=24)
    old_rooms = NrtPrivateChatRoom.objects.filter(created_at__lt=threshold)
    old_rooms.delete()
        # context['looped'] = 'successfuly deleted older rooms'

    if request.method == 'POST':

        # print(request.POST)
        try:
            activated_list = AllActivatedUsers.objects.get(pk=1)
        except AllActivatedUsers.DoesNotExist:
            activated_list = AllActivatedUsers.objects.create(pk=1)
            activated_list.save()
        
        if 'activate' in request.POST:
            # Handle Form 1 submission
            added = activated_list.add_user(user)
            print('added - ', added)
            context['status'] = True
            # return render(request, "nrt/nrt_text.html", context)

        elif 'deactivate' in request.POST:
            # Handle Form 2 submission
            removed = activated_list.remove_user(user)
            print('removed - ', removed)
            context['status'] = False

            ''' also have to remove this user from all the nrtrooms it is been a part of  '''
            NrtPrivateChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user)).delete()
            # return render(request, "nrt/nrt_text.html", context)

        elif 'skip_date' in request.POST:
            NrtPrivateChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user)).delete()
            return redirect('nrt-text')


        elif 'find_me_date' in request.POST:
            # we have to find a fuckin date for this bastard
            try:
                room = NrtPrivateChatRoom.objects.filter(Q(user1=user) | Q(user2=user) & Q(is_active=True)).first()
                if room:
                    # check if this room is not older than 24 hrs because if yes than delete it 
                    created_at = room.created_at  # Replace 'created_at' with the actual field name

                    # Calculate the time difference
                    time_difference = timezone.now() - created_at

                    # Check if the time difference is greater than 24 hours
                    if time_difference.total_seconds() > 24 * 3600:  # 24 hours in seconds
                        print("The room is more than 24 hours old.")
                        # so we are deleting this room
                        room.delete()
                        print('room was older than 24 hrs so deleted')
                        room = None
                    


                if room:
                    # woah this user is a part of a room now we have to fetch its chats and messages show her/him
                    print('This use is a part already a part of the group handle it properly - ', room)
                    context['room'] = room

                    'add ice breaker to the room first fetch a random icebreaker'
                    if room.icebreaker:
                        context['ice_ques'] = room.icebreaker
                        context['hide_ice'] = 'yes'
                    else:
                        iceques = random_icebreaker()
                        room.icebreaker = iceques
                        room.save()
                        if iceques:
                            context['ice_ques'] = room.icebreaker
                            context['hide_ice'] = 'no'

                
                    
                    if room.user1 == request.user:
                        # other_user_name = room.user2.name + ' | ' + room.user2.university_name
                        other_user_name = room.user2.name 
                        other_user_id = room.user2.id
                        last_seen = room.user2.last_activity
                        other_user = room.user2
                    else:
                        # other_user_name =  room.user1.name + ' | ' + room.user1.university_name
                        other_user_name =  room.user1.name 
                        other_user_id =  room.user1.id 
                        last_seen = room.user1.last_activity
                        other_user = room.user2

                    context['last_seen'] = last_seen
                    context['other_user_name'] = other_user_name
                    context['other_user_id'] = other_user_id
                    context['status'] = True

                    meet_perci = meetup_percentage(room,request.user)
                    if meet_perci == 100:
                        print('damn this perci is 100')
                        context['meetup_unlocked'] = 'yes'

                    context['meetup_perci'] = meet_perci
                    print(meet_perci, 'this is the meetup peri peri perci now')


                    try:
                        got_req = Meetup.objects.filter((Q(user1=other_user) | Q(user2=other_user)) & Q(room=room) & Q(is_fixed = False)).first()
                        print('got_req -',got_req,other_user)
                        i_send = Meetup.objects.filter((Q(user1=request.user) | Q(user2=request.user)) & Q(room=room) & Q(is_fixed = False)).first()
                        print('i_send_req -',i_send)
                        is_fixed = Meetup.objects.filter(Q(is_fixed = True) & Q(room=room)).first()
                        print('is_Already_fixed -',is_fixed)
                    except Meetup.DoesNotExist:
                        print('error fetching meetup')

                    if got_req:
                        # This means the other user has sent this user a meetup req
                        context['got_req'] = 'yes'
                        if request.user.gender == 'M':
                            context['address'] = got_req.address1
                            context['date'] = got_req.datetime.date()
                            context['time'] = got_req.datetime.time()
                        print('so this is passed right? nope')

                    elif i_send:
                        # This means this fucker has send the req meetup to other user
                        context['i_send'] = 'yes'
                        if request.user.gender == 'F':
                            context['address'] = i_send.address1
                            context['date'] = i_send.datetime.date()
                            context['time'] = i_send.datetime.time()
                        print('so this is passed right? maybe', i_send)


                    elif is_fixed:
                        # Bitch their date is fixed wowww
                        context['meetup_fixed'] = 'yes'
                        context['address'] = is_fixed.address1
                        context['date'] = is_fixed.datetime.date()
                        context['time'] = is_fixed.datetime.time()
                        print('so this is passed right?')

                    print('bhenchod mereko call ni kara 1')


                    room_created_at = room.created_at
                    # Calculate the remaining time in seconds
                    current_time = timezone.now()
                    time_difference = abs((room_created_at - current_time).total_seconds())
                    print('the duckin time difference - ', time_difference)
                    remaining_time_seconds = max(0, 86400 - time_difference)
                    context['remaining_time_seconds'] = remaining_time_seconds
                    print('the remaining time is this - ', remaining_time_seconds)
                    '''
                    This means the user have a chat , so we are giving them a skip button! to reject this chat and go back to find_me_a_date
                    '''
                    context['show_skip'] = 'skip'
                    # return HttpResponse(f'you are already connected at this room - {room} ')
                else:
                    print('This user is not a part of any group this means he/she is not already connected or a part of blind date')

                    """
                    Now we gotta find a date for this bastard and throw him/her into chat with them.
                    """

                    # wut the room doesn't exist so now we gotta create one here 
                    ''' The user doesn't have any room so we are gonna fetch all the nearby activated users that are not grouped and connect this user with them '''

                    # first fetch all activated users and create a set of all nearby activated users

                    all_activated_users = activated_list.users.all() # these are all the activated users

                    print('all activated users - ', all_activated_users)
                    

                        # have to fetch all nearby users
                    university = University.objects.get(name=user.university_name)
                    all_nearby_users = university.allNearbyUsers.all()

                    print('all_nearby_users - ', all_nearby_users)

                    all_nearby_activated_users = set()

                    for kid in all_nearby_users:
                        if kid != request.user:
                            if kid in all_activated_users:
                                all_nearby_activated_users.add(kid)

                    # now we have all nearby activated users , now we want all of those users which are not currently a part of any group

                    print('all nearby activated users - ', all_nearby_activated_users)

                    all_ungrouped_nearby_activated_kids = set()

                    for kid in all_nearby_activated_users:
                        is_grouped = nrt_grouped_status(kid)
                        if not is_grouped:
                            all_ungrouped_nearby_activated_kids.add(kid)

                    print('all_ungrouped_nearby_activated_kids - ', all_ungrouped_nearby_activated_kids)

                    if len(all_ungrouped_nearby_activated_kids) == 0:
                        context['unavaillable'] = 'Sorry all other other users are either grouped or has not activated this feature yet!'
                        context['status'] = True

                    else:
                        # now we have all the fucking ungrouped nearby activated students

                        # now remove all the users from it with whom i have already connected within 24 hrs
                        all_ungrouped_nearby_activated_kids_24hrs_older = set()
                        for mc in all_ungrouped_nearby_activated_kids:
                            user1 = request.user
                            user2 = mc

                            try:
                                existing_connection = MeetupConnection.objects.filter(user1=user1, user2=user2).first()
                                if not existing_connection:
                                    existing_connection = MeetupConnection.objects.filter(user1=user2, user2=user1).first()
                            except MeetupConnection.DoesNotExist:
                                print('idk man')

                            if existing_connection:
                                # Check if the existing connection is older than 24 hours
                                if ((timezone.now() - existing_connection.connection_time) > timedelta(hours=24)):
                                    # update the connection time since the existing one is older than 24 hours
                                    all_ungrouped_nearby_activated_kids_24hrs_older.add(mc)
                                else:
                                    continue
                            else:
                                all_ungrouped_nearby_activated_kids_24hrs_older.add(mc)
                                
                        print('These kids are all the ungrouped nearby activated kids',all_ungrouped_nearby_activated_kids)
                        print('These kids are all the ungrouped nearby activated kids who are not connected with me in the past 24 hrs',all_ungrouped_nearby_activated_kids_24hrs_older)
                        other_stranger = get_random_user(list(all_ungrouped_nearby_activated_kids_24hrs_older), request.user.gender)
                        

                        if other_stranger:

                            # now we have selected the other stranger we want to create a chatroom of this user with the other stranger 

                            super_chat_room = NrtPrivateChatRoom(user1=request.user, user2=other_stranger)
                            super_chat_room.save()

                            try:
                                existing_connection = MeetupConnection.objects.filter(user1=request.user, user2=other_stranger).first()
                                if existing_connection:
                                    existing_connection.connection_time = timezone.now()
                                    existing_connection.save()
                                else:
                                    existing_connection = MeetupConnection.objects.filter(user1=other_stranger, user2=request.user).first()
                                    if existing_connection:
                                        existing_connection.connection_time = timezone.now()
                                        existing_connection.save()
                                    else:
                                        # this means the connection doesnot exist so we will create a record
                                        print('creating the connection since it didn existed')
                                        new_connection = MeetupConnection(user1=request.user, user2=other_stranger)
                                        new_connection.save()

                            except MeetupConnection.DoesNotExist:
                                print('idk man')
                            print('The other stranger is this one - ', other_stranger)

                            print('This is the created room - ', super_chat_room)

                            # now the room is created and we have to through this room back to the ui (of current user)

                            context['room'] = super_chat_room
                            room = super_chat_room
                            'add ice breaker to the room first fetch a random icebreaker'
                            if room.icebreaker:
                                context['ice_ques'] = room.icebreaker
                                context['hide_ice'] = 'yes'
                            else:
                                iceques = random_icebreaker()
                                room.icebreaker = iceques
                                room.save()
                                if iceques:
                                    context['ice_ques'] = room.icebreaker
                                    context['hide_ice'] = 'no'
                            
                            if room.user1 == request.user:
                                # other_user_name = room.user2.name + ' | ' + room.user2.university_name
                                other_user_name = room.user2.name 
                                other_user_id = room.user2.pk
                                last_seen = room.user2.last_activity
                            else:
                                # other_user_name =  room.user1.name + ' | ' + room.user1.university_name
                                other_user_name =  room.user1.name 
                                other_user_id =  room.user1.pk 
                                last_seen = room.user1.last_activity

                            context['last_seen'] = last_seen
                            context['other_user_name'] = other_user_name
                            context['other_user_id'] = other_user_id
                            context['status'] = True


                            print('bhencho why 2 is gettin called')

                            room_created_at = room.created_at
                            # Calculate the remaining time in seconds
                            current_time = timezone.now()
                            time_difference = abs((room_created_at - current_time).total_seconds())
                            print('the duckin time difference - ', time_difference)
                            remaining_time_seconds = max(0, 86400 - time_difference)
                            context['remaining_time_seconds'] = remaining_time_seconds
                            print('the remaining time is this - ', remaining_time_seconds)

                            '''
                            This means the user have a chat , so we are giving them a skip button! to reject this chat and go back to find_me_a_date
                            '''
                            context['show_skip'] = 'skip'
                        else:
                            context['status'] = True
                            string_for_male = 'Sorry all other female users are already connected with someone at this moment. once connected the connection lasts for 24 hrs so please either try again later or tommorow...'
                            string_for_female = 'Sorry all other male users are already connected with someone at this moment. once connected the connection lasts for 24 hrs so please either try again later or tommorow...'

                            if request.user.gender == 'M':
                                context['unavaillable'] = string_for_male
                            elif request.user.gender == 'F':
                                context['unavaillable'] = string_for_female
                            else:
                                context['unavaillable'] = 'Sorry all other users are already connected with someone at this moment. once connected the connection lasts for 24 hrs so please either try again later or tommorow...'

                        
            except NrtPrivateChatRoom.DoesNotExist:
                print('error occured fetching nrtprivatechatroom')

            return render(request, "nrt/nrt_text.html", context)

        return redirect('nrt-text')
    else:

        try:
            activated_list = AllActivatedUsers.objects.get(pk=1)
        except AllActivatedUsers.DoesNotExist:
            activated_list = AllActivatedUsers.objects.create(pk=1)
            activated_list.save()
        
        if user in activated_list.users.all():
            context['status'] = True

            ''' so now the user is that one which has already activated this feature, now we wanna check whether he/she is already joined with someone or not because if joined than show the chatroom if not than connect it with someone '''
            
            try:
                room = NrtPrivateChatRoom.objects.filter(Q(user1=user) | Q(user2=user) & Q(is_active=True)).first()
                # check if this room is not older than 24 hrs because if yes than delete it 
                if room:
                    created_at = room.created_at  # Replace 'created_at' with the actual field name

                    # Calculate the time difference
                    time_difference = timezone.now() - created_at

                    # Check if the time difference is greater than 24 hours
                    if time_difference.total_seconds() > 24 * 3600:  # 24 hours in seconds
                        print("The room is more than 24 hours old.")
                        # so we are deleting this room
                        room.delete()
                        print('room was older than 24 hrs so deleted')
                        room = None

                if room:
                    # woah this user is a part of a room now we have to fetch its chats and messages show her/him
                    print('This use is a part already a part of the group handle it properly - ', room)
                    context['room'] = room
                    'add ice breaker to the room first fetch a random icebreaker'
                    if room.icebreaker:
                        context['ice_ques'] = room.icebreaker
                        context['hide_ice'] = 'yes'
                    else:
                        iceques = random_icebreaker()
                        room.icebreaker = iceques
                        room.save()
                        if iceques:
                            context['ice_ques'] = room.icebreaker
                            context['hide_ice'] = 'yes'
                    if room.user1 == request.user:
                        # other_user_name = room.user2.name + ' | ' + room.user2.university_name
                        other_user_name = room.user2.name 
                        other_user_id = room.user2.id 
                        last_seen = room.user2.last_activity
                        other_user = room.user2
                    else:
                        # other_user_name =  room.user1.name + ' | ' + room.user1.university_name
                        other_user_name =  room.user1.name 
                        other_user_id =  room.user1.id 
                        last_seen = room.user1.last_activity
                        other_user = room.user1

                    context['last_seen'] = last_seen
                    context['other_user_id'] = other_user_id
                    meet_perci = meetup_percentage(room,request.user)
                    if meet_perci == 100:
                        print('damn this perci is 100')
                        context['meetup_unlocked'] = 'yes'

                    context['meetup_perci'] = meet_perci
                    print(meet_perci, 'this is the meetup peri peri perci now')

                    try:
                        got_req = Meetup.objects.filter((Q(user1=other_user) | Q(user2=other_user)) & Q(room=room) & Q(is_fixed = False)).first()
                        print('got_req -',got_req)
                        i_send = Meetup.objects.filter((Q(user1=request.user) | Q(user2=request.user)) & Q(room=room) & Q(is_fixed = False)).first()
                        print('i_send_req -',i_send)
                        is_fixed = Meetup.objects.filter(Q(is_fixed = True) & Q(room=room)).first()
                        print('is_Already_fixed -',is_fixed)
                    except Meetup.DoesNotExist:
                        print('error fetching meetup')

                    if got_req:
                        # This means the other user has sent this user a meetup req
                        context['got_req'] = 'yes'
                        if request.user.gender == 'M':
                            context['address'] = got_req.address1
                            context['date'] = got_req.datetime.date()
                            context['time'] = got_req.datetime.time()
                        print('so this is passed right? nope')

                    elif i_send:
                        # This means this fucker has send the req meetup to other user
                        context['i_send'] = 'yes'
                        if request.user.gender == 'F':
                            context['address'] = i_send.address1
                            context['date'] = i_send.datetime.date()
                            context['time'] = i_send.datetime.time()
                        print('so this is passed right? maybe', i_send)


                    elif is_fixed:
                        # Bitch their date is fixed wowww
                        context['address'] = is_fixed.address1
                        context['date'] = is_fixed.datetime.date()
                        context['time'] = is_fixed.datetime.time()
                        context['meetup_fixed'] = 'yes'
                        print('so this is passed right?')

                    print('bhencho fuck u zindagi', is_fixed)
            

                    room_created_at = room.created_at
                    # Calculate the remaining time in seconds
                    current_time = timezone.now()
                    time_difference = abs((room_created_at - current_time).total_seconds())
                    print('the duckin time difference - ', time_difference)
                    remaining_time_seconds = max(0, 86400 - time_difference)
                    context['remaining_time_seconds'] = remaining_time_seconds
                    print('the remaining time is this - ', remaining_time_seconds)

                    context['other_user_name'] = other_user_name
                    '''
                    This means the user have a chat , so we are giving them a skip button! to reject this chat and go back to find_me_a_date
                    '''
                    context['show_skip'] = 'skip'
                    # return HttpResponse(f'you are already connected at this room - {room} ')
                else:
                    print('This user is not a part of any group this means he/she is not already connected or a part of blind date')

                    """
                    Now we gotta show this bastard a find a blind date for me button
                    """

                    context['find_me_date'] = 'find_me_date'

                    # # wut the room doesn't exist so now we gotta create one here 
                    # ''' The user doesn't have any room so we are gonna fetch all the nearby activated users that are not grouped and connect this user with them '''

                    # # first fetch all activated users and create a set of all nearby activated users

                    # all_activated_users = activated_list.users.all() # these are all the activated users

                    # print('all activated users - ', all_activated_users)
                    

                    #     # have to fetch all nearby users
                    # university = University.objects.get(name=user.university_name)
                    # all_nearby_users = university.allNearbyUsers.all()

                    # print('all_nearby_users - ', all_nearby_users)

                    # all_nearby_activated_users = set()

                    # for kid in all_nearby_users:
                    #     if kid != request.user:
                    #         if kid in all_activated_users:
                    #             all_nearby_activated_users.add(kid)

                    # # now we have all nearby activated users , now we want all of those users which are not currently a part of any group

                    # print('all nearby activated users - ', all_nearby_activated_users)

                    # all_ungrouped_nearby_activated_kids = set()

                    # for kid in all_nearby_activated_users:
                    #     is_grouped = nrt_grouped_status(kid)
                    #     if not is_grouped:
                    #         all_ungrouped_nearby_activated_kids.add(kid)

                    # print('all_ungrouped_nearby_activated_kids - ', all_ungrouped_nearby_activated_kids)

                    # if len(all_ungrouped_nearby_activated_kids) == 0:
                    #     context['unavaillable'] = 'Sorry all other users are either already grouped or has not activated this feature yet try again later....'

                    # else:
                    #     # now we have all the fucking ungrouped nearby activated students

                    #     other_stranger = get_random_user(list(all_ungrouped_nearby_activated_kids), request.user.gender)
                    #     print('The other stranger is this one - ', other_stranger)

                    #     # now we have selected the other stranger we want to create a chatroom of this user with the other stranger 

                    #     super_chat_room = NrtPrivateChatRoom(user1=request.user, user2=other_stranger)
                    #     super_chat_room.save()

                    #     print('This is the created room - ', super_chat_room)

                    #     # now the room is created and we have to through this room back to the ui (of current user)

                        # context['room'] = super_chat_room
                        
                        # return render(request, "nrt/nrt_text.html", context)

            except NrtPrivateChatRoom.DoesNotExist:
                print('error occured fetching nrtprivatechatroom')

            return render(request, "nrt/nrt_text.html", context)

        else:
            context['status'] = False
            return render(request, "nrt/nrt_text.html", context)
    
    return render(request, "nrt/nrt_text.html", context)



    # try:


    #     # Redirect them if not authenticated
    #     if not user.is_authenticated:
    #         return redirect("login")

    #     if room_id:
    #         try:
    #             room = PrivateChatRoom.objects.get(pk=room_id)
    #             context["room"] = room
    #         except PrivateChatRoom.DoesNotExist:
    #             return HttpResponse('The room you are trying to access does not exist.')

    #     # 1. Find all the rooms this user is a part of
    #     rooms1 = PrivateChatRoom.objects.filter(user1=user, is_active=True)
    #     rooms2 = PrivateChatRoom.objects.filter(user2=user, is_active=True)

    #     # 2. merge the lists
    #     rooms = list(chain(rooms1, rooms2))
    #     print(str(len(rooms)))

    #     """
    #     m_and_f:
    #         [{"message": "hey", "friend": "Mitch"}, {
    #             "message": "You there?", "friend": "Blake"},]
    #     Where message = The most recent message
    #     """
    #     m_and_f = []
    #     for room in rooms:
    #         # Figure out which user is the "other user" (aka friend)
    #         if room.user1 == user:
    #             friend = room.user2
    #         else:
    #             friend = room.user1

    #         '''
    #         Fetching all the unread messages send by the friend to me (in our room)
    #         '''

    #         unread_messages = RoomChatMessage.objects.filter(
    #             Q(room=room) & Q(user=friend) & Q(read=False))
    #         unread_messages_count = unread_messages.count()

    #         m_and_f.append({
    #             'unread_messages_count': unread_messages_count,
    #                 'friend': friend
    #         })

    #     context['m_and_f'] = m_and_f
    #     context['debug'] = DEBUG
    #     context['id'] = request.user.id
    #     context['debug_mode'] = settings.DEBUG
    # except Exception as e:
    #     print(e)
    return render(request, "nrt/nrt_text.html", context)

# Ajax call to return a private chatroom or create one if does not exist


# def create_or_return_private_chat(request, *args, **kwargs):
#     user1 = request.user
#     payload = {}
#     if user1.is_authenticated:
#         if request.method == "POST":
#             user2_id = request.POST.get("user2_id")
#             try:
#                 user2 = Account.objects.get(pk=user2_id, is_verified = True)
#                 chat = find_or_create_private_chat(user1, user2)
#                 payload['response'] = "Successfully got the chat."
#                 payload['chatroom_id'] = chat.id
#             except Account.DoesNotExist:
#                 payload['response'] = "Unable to start a chat with that user."
#     else:
#         payload['response'] = "You can't start a chat if you are not authenticated."
#     return HttpResponse(json.dumps(payload), content_type="application/json")


# def report_view(request, *args, **kwargs):

#     print('The flag view is called')
#     user = request.user

#     if not request.user.is_authenticated:
#         return redirect("login")

#     if request.POST:
#         try:
#             flag_user_id = request.POST.get('flag_user_id')
#             flag_user_name = request.POST.get('flag_user_name')
#             reason = request.POST.get('flag-reason')
            
#             account = Account.objects.get(pk=flag_user_id, is_verified = True)
            
#             flag_object = Flags.objects.filter(user=account, Flagger=user)
            
#             if flag_object.exists():
#                 response_data = {
#                     'status' : "Already Flagged",
#                     'message' : 'You have already flagged this User!'
#             }
#             else:
#                 account.flags = account.flags + 1
#                 account.save()
                
#                 flag = Flags(flag_user_id=flag_user_id, user=account,
# 							reason=reason, Flagger=user)
#                 flag.save()
#                 response_data = {
#                     'status' : 'Flagged',
# 					'message': 'This Person has been reported!'
# 				}

#         except Exception as e:
#             print('The flag exception is - ', str(e))
#             response_data = {
#                 'status' : 'error',
#                 'message': str(e),
#             }

#     return HttpResponse(json.dumps(response_data), content_type="application/json")


def nrt_grouped_status(kid):

    room = NrtPrivateChatRoom.objects.filter(Q(user1=kid) | Q(user2=kid) & Q(is_active=True)).first()
    if room:
        is_grouped = True
    else:
        is_grouped = False
    return is_grouped

# def get_random_user(student_list, current_user_gender):

#     try:

#         # Split the student list into opposite and same gender lists
#         opposite_gender_list = [student for student in student_list if student.gender != current_user_gender]
#         same_gender_list = [student for student in student_list if student.gender == current_user_gender]

#         # Determine the probability for opposite and same gender
#         opposite_gender_probability = 0.7
#         same_gender_probability = 0.3

#         # Randomly select a user based on the probabilities
#         if random.uniform(0, 1) < opposite_gender_probability and opposite_gender_list:
#             selected_user = random.choice(opposite_gender_list)
#         elif same_gender_list:
#             selected_user = random.choice(same_gender_list)
#         else:
#             # If one of the lists is empty, select from the other
#             selected_user = random.choice(student_list)

#         return selected_user

#     except Exception as e:
#         print('The exception at fetching nrt user - ', str(e))
#         return None



def get_random_user(student_list, current_user_gender):
    try:
        # Filter the student list to get only opposite gender users
        opposite_gender_list = [student for student in student_list if student.gender != current_user_gender]

        # If there are opposite gender users, randomly select one; otherwise, return None
        selected_user = random.choice(opposite_gender_list) if opposite_gender_list else None

        return selected_user

    except Exception as e:
        print('The exception at fetching next user - ', str(e))
        return None
    
def meetup_percentage(room,user):

    try:

        # room = NrtPrivateChatRoom.objects.filter(id=roomva).first()
        if room.user1 == user:
            friend = room.user2
        else:
            friend = room.user1

        # first gotta fetch total messages in the room
        # total_messages = NrtRoomChatMessage.objects.filter(room=room).count()
        
        # now fetch the messages sent by this user
        user1_messages = NrtRoomChatMessage.objects.filter(Q(room=room) & Q(user=user)).count()

        # now fetch the messages sent by other user
        user2_messages = NrtRoomChatMessage.objects.filter(Q(room=room) & Q(user=friend)).count()

        print('The user 1 messages - ', user1_messages)

        # now calculate the percentage
        '''
        each user can reach 50 percent by sending 6 messages 
        '''

        if user1_messages > 6:
            user1_messages = 6
        
        if user2_messages > 6:
            user2_messages = 6
        
        print('good till now')
        percentage = int(((user1_messages + user2_messages)/12)*100)
        print('fucked - ', percentage)
        percentage = min(100,percentage)
    except Exception as e:
        print('exception while calculating meetup perci - ', str(e))
        percentage = 0   
    return percentage

def random_icebreaker():
    icebreakers = NrtIceBreakers.objects.all()
    if icebreakers:
        random_question = random.choice(icebreakers)
        return random_question.question
    return None