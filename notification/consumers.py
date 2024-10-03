from django.conf import settings
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.paginator import Paginator
from django.core.serializers import serialize
from channels.db import database_sync_to_async
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from itertools import chain

import json
from datetime import datetime, timedelta

from friend.models import FriendRequest, FriendList
from chat.models import RoomChatMessage, PrivateChatRoom
from nrt.models import  NrtRoomChatMessage , NrtPrivateChatRoom
from notification.utils import LazyNotificationEncoder
from notification.constants import *
from notification.models import Notification, Notif
from notification.models import  ActiveUsers, ActiveVideoUsers
from mystranger_app.models import University, UniversityProfile
from chat.exceptions import ClientError
from account.models import Account
from qna.models import Answer
from confessions.models import CAnswer

from datetime import datetime, timedelta
from django.utils import timezone
from firebase_admin import messaging
from mystranger.settings import domain_name
# from CodingWithMitchChat.settings import domain_name

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    Passing data to and from header.html. Notifications are displayed as "drop-downs" in the nav bar.
    There is two major categories of notifications:
            1. General Notifications
                    1. FriendRequest
                    2. FriendList
            1. Chat Notifications
                    1. UnreadChatRoomMessages
    """

    async def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        # print("NotificationConsumer: connect: " + str(self.scope["user"]))
        await self.accept()
        
        

    async def disconnect(self, code):
        """
        Called when the WebSocket closes for any reason.
        """
        print('Adding -1 to count')
        user = self.scope['user']
        if user.is_authenticated:
            count = await maintain_count(False, user)
        '''
        These are though going to be called even when user is not in the video or text page but they are not going to affect anything because the user is only going to get remove if it existed in the list at first place therefore in unneccessary calling its just going to get ignored.
        '''
        user = self.scope['user']
        if user.is_authenticated:
            user_removed_to_video_count = await add_or_remove_user_to_video_count(self.scope['user'], False)
            user_removed_to_text_count = await add_or_remove_user_to_text_count(self.scope['user'], False)

        print("NotificationConsumer: disconnect")

    async def receive_json(self, content):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        command = content.get("command", None)
        # print("NotificationConsumer: receive_json. Command: " + command)
        try:
            if command == "get_general_notifications":
                payload = await get_general_notifications(self.scope["user"], content.get("page_number", None))
                # print(payload)
                if payload == None or payload == '{}':
                    # print('There is no payload so pagination exhaustion')
                    await self.general_pagination_exhausted()
                else:
                    payload = json.loads(payload)

                    print('Printing the answer notifs ------')
                    # print(payload)
                    await self.send_general_notifications_payload(payload['notifications'], payload['new_page_number'])
            elif command == "get_new_general_notifications":
                payload = await get_new_general_notifications(self.scope["user"], content.get("newest_timestamp", None))
                if payload != None:
                    payload = json.loads(payload)
                    await self.send_new_general_notifications_payload(payload['notifications'])
            elif command == "accept_friend_request":
                notification_id = content['notification_id']
                payload = await accept_friend_request(self.scope['user'], notification_id)
                if payload == None:
                    raise ClientError(
                        '204', "Something went wrong. Try refreshing the browser.")
                else:
                    payload = json.loads(payload)
                    await self.send_updated_friend_request_notification(payload['notification'])
            elif command == "decline_friend_request":
                notification_id = content['notification_id']
                payload = await decline_friend_request(self.scope['user'], notification_id)
                if payload == None:
                    raise ClientError(
                        "Something went wrong. Try refreshing the browser.")
                else:
                    payload = json.loads(payload)
                    await self.send_updated_friend_request_notification(payload['notification'])
            elif command == "refresh_general_notifications":
                # print('The trouble')
                payload = await refresh_general_notifications(self.scope["user"], content['oldest_timestamp'], content['newest_timestamp'])
                # print('Is here')
                if payload == None:
                    # print('The payload is not present | payload == None')
                    raise ClientError(
                        204, "Something went wrong. Try refreshing the browser.")
                else:
                    payload = json.loads(payload)
                    # print(payload)
                    await self.send_general_refreshed_notifications_payload(payload['notifications'])
            elif command == "get_unread_general_notifications_count":
                payload = await get_unread_general_notification_count(self.scope["user"])
                if payload != None:
                    payload = json.loads(payload)
                    await self.send_unread_general_notification_count(payload['count'])
            elif command == "get_unread_msg_notifications_count":
                # print('The command is here ------------------------------')
                payload = await get_unread_message_notification_count(self.scope["user"])
                if payload != None:
                    payload = json.loads(payload)
                    await self.send_unread_msg_notification_count(payload['count'])
                else:
                    # print('bc no payload', payload)
                    pass
            elif command == "get_unread_bd_notifications_count":
                # print('The command is here to get bd notifs ------------------------------')
                payload = await get_unread_bd_message_notification_count(self.scope["user"])
                if payload != None:
                    payload = json.loads(payload)
                    # print('the fucking bd payload - ', payload['count'])
                    await self.send_unread_bd_msg_notification_count(payload['count'])
                else:
                    # print('bc no payload', payload)
                    pass
            elif command == "mark_notifications_read":
                await mark_notifications_read(self.scope["user"])
            elif command == 'add_active_users_count':
                # print('Adding +1 to count')
                count = await maintain_count(True,self.scope['user'])
                await self.send_json(
                    {
                        'active_count' : count
                    },
                )
            elif command == 'add_video_count':
                print('adding user to video count')
                user = self.scope['user']
                if user.is_authenticated:
                    user_added_to_video_count = await add_or_remove_user_to_video_count(self.scope['user'], True)
            elif command == 'add_text_count':
                user = self.scope['user']
                if user.is_authenticated:
                    print('adding user to text count')
                    user_added_to_text_count = await add_or_remove_user_to_text_count(self.scope['user'], True)
            elif command == 'refresh_active_count':
                await self.send_refresh_active_count()
            elif command == 'get_video_count':
                # print('called to fetch the count')
                await self.send_video_count()
            elif command == 'get_text_count':
                # print('called to fetch the count')
                await self.send_text_count()
            elif command == 'show_total_regs':
                # print('called to fetch the count')
                # print('the fuck i am getting called')
                await self.send_total_count()

        except Exception as e:
            # print("EXCEPTION: receive_json: " + str(e))
            pass

    async def display_progress_bar(self, shouldDisplay):
        # print("NotificationConsumer: display_progress_bar: " + str(shouldDisplay))
        await self.send_json(
            {
                "progress_bar": shouldDisplay,
            },
        )

    async def send_refresh_active_count(self):

        count = await fetch_active_count()
        await self.send_json(
            {
                'active_count' : count
            },
        )

    async def send_total_count(self):

        # print('am i really?')
        user = self.scope['user']
        if user.is_authenticated:
            try:
                total_count = await fetch_total_regs()
                # print(total_count)
                await self.send_json(
                {
                    'total_regs_count' : total_count
                },
            )

            except Exception as e:
                print('fuck - ',str(e))
        
    async def send_video_count(self):


        user = self.scope['user']

        if user.is_authenticated:
            count = await create_video_count(self.scope['user'])
            if count == 1 or count==None:
                count = 1
            # print('get video count is -', count)
            await self.send_json(
                {
                    'video_count' : count
                },
            )

    async def send_text_count(self):


        user = self.scope['user']
        if user.is_authenticated:
            count = await create_text_count(self.scope['user'])
            if count == 1 or count==None:
                count = 1
            # print('get text count is -', count)
            await self.send_json(
                {
                    'text_count' : count
                },
            )

    async def send_general_notifications_payload(self, notifications, new_page_number):
        """
        Called by receive_json when ready to send a json array of the notifications
        """
        # print("NotificationConsumer: send_general_notifications_payload")
        await self.send_json(
            {
                "general_msg_type": GENERAL_MSG_TYPE_NOTIFICATIONS_PAYLOAD,
                "notifications": notifications,
                "new_page_number": new_page_number,
            },
        )

    async def send_updated_friend_request_notification(self, notification):
        """
        After a friend request is accepted or declined, send the updated notification to template
        payload contains 'notification' and 'response':
        1. payload['notification']
        2. payload['response']
        """
        await self.send_json(
            {
                "general_msg_type": GENERAL_MSG_TYPE_UPDATED_NOTIFICATION,
                "notification": notification,
            },
        )

    async def general_pagination_exhausted(self):
        """
        Called by receive_json when pagination is exhausted for general notifications
        """
        # print("General Pagination DONE... No more notifications.")
        await self.send_json(
            {
                "general_msg_type": GENERAL_MSG_TYPE_PAGINATION_EXHAUSTED,
            },
        )

    async def send_general_refreshed_notifications_payload(self, notifications):
        """
        Called by receive_json when ready to send a json array of the notifications
        """
        #print("NotificationConsumer: send_general_refreshed_notifications_payload: " + str(notifications))
        await self.send_json(
            {
                "general_msg_type": GENERAL_MSG_TYPE_NOTIFICATIONS_REFRESH_PAYLOAD,
                "notifications": notifications,
            },
        )

    async def send_new_general_notifications_payload(self, notifications):
        """
        Called by receive_json when ready to send a json array of the notifications
        """
        await self.send_json(
            {
                "general_msg_type": GENERAL_MSG_TYPE_GET_NEW_GENERAL_NOTIFICATIONS,
                "notifications": notifications,
            },
        )

    async def send_unread_general_notification_count(self, count):
        """
        Send the number of unread "general" notifications to the template
        """
        await self.send_json(
            {
                "general_msg_type": GENERAL_MSG_TYPE_GET_UNREAD_NOTIFICATIONS_COUNT,
                "count": count,
            },
        )

    async def send_unread_msg_notification_count(self, count):
        """
        Send the number of unread "general" msg notifications count to the template
        """
        GENERAL_MSG_TYPE_GET_UNREAD_MSG_NOTIFICATIONS_COUNT = 8
        await self.send_json(
            {
                "general_msg_type": GENERAL_MSG_TYPE_GET_UNREAD_MSG_NOTIFICATIONS_COUNT,
                "count": count,
            },
        )

    async def send_unread_bd_msg_notification_count(self, count):
        """
        Send the number of unread "general" msg notifications count to the template
        """
        GENERAL_MSG_TYPE_GET_UNREAD_MSG_NOTIFICATIONS_COUNT = 9
        await self.send_json(
            {
                "general_bd_msg_type": GENERAL_MSG_TYPE_GET_UNREAD_MSG_NOTIFICATIONS_COUNT,
                "count": count,
            },
        )


@database_sync_to_async
def get_general_notifications(user, page_number):
    """
    Get General Notifications with Pagination (next page of results).
    This is for appending to the bottom of the notifications list.
    General Notifications are:
    1. FriendRequest
    2. FriendList
    """
    if user.is_authenticated:
        friend_request_ct = ContentType.objects.get_for_model(FriendRequest)
        friend_list_ct = ContentType.objects.get_for_model(FriendList)
        answer_list_ct = ContentType.objects.get_for_model(Answer)
        Canswer_list_ct = ContentType.objects.get_for_model(CAnswer)
        notifications = Notification.objects.filter(target=user, content_type__in=[
                                                    friend_request_ct, friend_list_ct, answer_list_ct, Canswer_list_ct]).order_by('-timestamp')
        print('These are the general notifs - ')
        # print(notifications)
        p = Paginator(notifications, DEFAULT_NOTIFICATION_PAGE_SIZE)

        payload = {}
        if len(notifications) > 0:
            if int(page_number) <= p.num_pages:
                s = LazyNotificationEncoder()
                serialized_notifications = s.serialize(
                    p.page(page_number).object_list)
                payload['notifications'] = serialized_notifications
                new_page_number = int(page_number) + 1
                payload['new_page_number'] = new_page_number
        else:
            return None
    else:
        raise ClientError("User must be authenticated to get notifications.")

    return json.dumps(payload)


@database_sync_to_async
def accept_friend_request(user, notification_id):
    """
    Accept a friend request
    """
    payload = {}
    if user.is_authenticated:
        try:
            notification = Notification.objects.get(pk=notification_id)
            friend_request = notification.content_object
            # confirm this is the correct user
            if friend_request.receiver == user:
                # accept the request and get the updated notification
                updated_notification = friend_request.accept()

                # return the notification associated with this FriendRequest
                s = LazyNotificationEncoder()
                payload['notification'] = s.serialize(
                    [updated_notification])[0]
                return json.dumps(payload)
        except Notification.DoesNotExist:
            raise ClientError(
                "An error occurred with that notification. Try refreshing the browser.")
    return None


@database_sync_to_async
def decline_friend_request(user, notification_id):
    """
    Decline a friend request
    """
    payload = {}
    if user.is_authenticated:
        try:
            notification = Notification.objects.get(pk=notification_id)
            friend_request = notification.content_object
            # confirm this is the correct user
            if friend_request.receiver == user:
                # accept the request and get the updated notification
                updated_notification = friend_request.decline()

                # return the notification associated with this FriendRequest
                s = LazyNotificationEncoder()
                payload['notification'] = s.serialize(
                    [updated_notification])[0]
                return json.dumps(payload)
        except Notification.DoesNotExist:
            raise ClientError(
                "An error occurred with that notification. Try refreshing the browser.")
    return None


@database_sync_to_async
def refresh_general_notifications(user, oldest_timestamp, newest_timestamp):
    """
    Retrieve the general notifications newer than the oldest one on the screen and younger than the newest one the screen.
    The result will be: Notifications currently visible will be updated
    """
    payload = {}
    if user.is_authenticated:
        # print(oldest_timestamp)
        # remove timezone because who cares
        oldest_ts = oldest_timestamp[0:oldest_timestamp.find("+")]
        # print(oldest_ts)
        oldest_ts = datetime.strptime(str(oldest_ts), '%Y-%m-%d %H:%M:%S.%f')
        # print(oldest_ts)
        # print('This is empty', newest_timestamp)
        # remove timezone because who cares
        newest_ts = newest_timestamp[0:newest_timestamp.find("+")]
        # print(newest_ts)
        newest_ts = datetime.strptime(newest_ts, '%Y-%m-%d %H:%M:%S.%f')
        newest_ts = newest_ts + timedelta(seconds=2)
        newest_ts = newest_ts.strftime('%Y-%m-%d %H:%M:%S.%f')
        # print(newest_ts)
        friend_request_ct = ContentType.objects.get_for_model(FriendRequest)
        friend_list_ct = ContentType.objects.get_for_model(FriendList)
        answer_list_ct = ContentType.objects.get_for_model(Answer)
        Canswer_list_ct = ContentType.objects.get_for_model(CAnswer)
        notifications = Notification.objects.filter(target=user, content_type__in=[
                                                    friend_request_ct, friend_list_ct, answer_list_ct, Canswer_list_ct], timestamp__gte=oldest_ts, timestamp__lte=newest_ts).order_by('-timestamp')

        s = LazyNotificationEncoder()
        payload['notifications'] = s.serialize(notifications)
    else:
        raise ClientError(
            204, "User must be authenticated to get notifications.")

    return json.dumps(payload)


@database_sync_to_async
def get_new_general_notifications(user, newest_timestamp):
    """
    Retrieve any notifications newer than the newest_timestatmp on the screen.
    """
    payload = {}
    if user.is_authenticated:
        # remove timezone because who cares
        timestamp = newest_timestamp[0:newest_timestamp.find("+")]
        timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
        friend_request_ct = ContentType.objects.get_for_model(FriendRequest)
        friend_list_ct = ContentType.objects.get_for_model(FriendList)
        answer_list_ct = ContentType.objects.get_for_model(Answer)
        Canswer_list_ct = ContentType.objects.get_for_model(CAnswer)
        notifications = Notification.objects.filter(target=user, content_type__in=[
                                                    friend_request_ct, friend_list_ct, answer_list_ct, Canswer_list_ct], timestamp__gt=timestamp, read=False).order_by('-timestamp')
        s = LazyNotificationEncoder()
        payload['notifications'] = s.serialize(notifications)
        payload['notifications'] = s.serialize(notifications)
    else:
        raise ClientError("User must be authenticated to get notifications.")

    return json.dumps(payload)


@database_sync_to_async
def get_unread_general_notification_count(user):
    payload = {}
    if user.is_authenticated:
        friend_request_ct = ContentType.objects.get_for_model(FriendRequest)
        friend_list_ct = ContentType.objects.get_for_model(FriendList)
        answer_list_ct = ContentType.objects.get_for_model(Answer)
        Canswer_list_ct = ContentType.objects.get_for_model(CAnswer)
        notifications = Notification.objects.filter(target=user, content_type__in=[
                                                    friend_request_ct, friend_list_ct, answer_list_ct, Canswer_list_ct], read=False)

        unread_count = 0
        if notifications:
            for notification in notifications.all():
                if not notification.read:
                    unread_count = unread_count + 1
        payload['count'] = unread_count
        return json.dumps(payload)
    else:
        raise ClientError("User must be authenticated to get notifications.")
    return None


@database_sync_to_async
def mark_notifications_read(user):
    """
    marks a notification as "read"
    """
    # print('Tf read is not getting called')
    if user.is_authenticated:
        notifications = Notification.objects.filter(target=user)
        if notifications:
            for notification in notifications.all():
                notification.read = True
                notification.save()
    return



@database_sync_to_async
def get_unread_message_notification_count(user):
    payload = {}
    if user.is_authenticated:
        rooms1 = PrivateChatRoom.objects.filter(user1=user, is_active=True)
        rooms2 = PrivateChatRoom.objects.filter(user2=user, is_active=True)

    # 2. merge the lists
        rooms = list(chain(rooms1, rooms2))
        count = 0
        for room in rooms:
            # Figure out which user is the "other user" (aka friend)
            if room.user1 == user:
                friend = room.user2
            else:
                friend = room.user1
            unread_messages_count = RoomChatMessage.objects.filter(
                Q(room=room) & Q(user=friend) & Q(read=False)).count()
            count += unread_messages_count
        payload['count'] = count
        # print('The total unread msg for user - ', user, 'is - ', count)
        return json.dumps(payload)

    else:
        raise ClientError("User must be authenticated to get notifications.")
    return None

@database_sync_to_async
def get_unread_bd_message_notification_count(user):
    payload = {}
    if user.is_authenticated:
        rooms1 = NrtPrivateChatRoom.objects.filter(user1=user, is_active=True)
        rooms2 = NrtPrivateChatRoom.objects.filter(user2=user, is_active=True)

    # 2. merge the lists
        rooms = list(chain(rooms1, rooms2))
        count = 0
        for room in rooms:
            # Figure out which user is the "other user" (aka friend)
            if room.user1 == user:
                friend = room.user2
            else:
                friend = room.user1
            unread_messages_count = NrtRoomChatMessage.objects.filter(
                Q(room=room) & Q(user=friend) & Q(read=False)).count()
            count += unread_messages_count
        payload['count'] = count
        # print('The total unread msg for user - ', user, 'is - ', count)
        return json.dumps(payload)

    else:
        raise ClientError("User must be authenticated to get notifications.")
    return None

@database_sync_to_async
def maintain_count(booli, user):
    try:
        count_obj = ActiveUsers.objects.get(pk=1)
        if booli:
            count_obj.add_user(user)
            count = count_obj.users.all().count()
        else:
            count_obj.remove_user(user)
            count = count_obj.users.all().count()
    except ActiveUsers.DoesNotExist:
        count_obj = ActiveUsers.objects.create(pk=1)
        if booli:
            count_obj.add_user(user)
            count = count_obj.users.all().count()
        else:
            count_obj.remove_user(user)
            count = count_obj.users.all().count()
    return count

@database_sync_to_async
def add_or_remove_user_to_video_count(user, booli):
    try:
        active_video_count = ActiveVideoUsers.objects.get(pk=1)
        if booli:
            active_video_count.add_user(user)
        else:
            active_video_count.remove_user(user)
    except ActiveVideoUsers.DoesNotExist:
        active_video_count = ActiveVideoUsers.objects.create(pk=1)
        if booli:
            active_video_count.add_user(user)
        else:
            active_video_count.remove_user(user)

@database_sync_to_async
def add_or_remove_user_to_text_count(user, booli):
    try:
        active_video_count = ActiveVideoUsers.objects.get(pk=2)
        if booli:
            active_video_count.add_user(user)
        else:
            active_video_count.remove_user(user)
    except ActiveVideoUsers.DoesNotExist:
        active_video_count = ActiveVideoUsers.objects.create(pk=2)
        if booli:
            active_video_count.add_user(user)
        else:
            active_video_count.remove_user(user)

@database_sync_to_async
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
        

        if count > 1:
            print('more than 10+ people are online')
            """
            so here we gotta send a notif to all the nearby users of this user that more than 10 are online plus also gotta check that the last notif was sent before one hr to avoid spamming
            """
            try:
                text_notif = Notif.objects.get(pk=1)
                # Get the current time
                current_time = timezone.now()

                # Calculate the time difference
                time_difference = current_time - text_notif.last_send

                # Compare if the time difference is greater than 1 hour
                if time_difference > timedelta(hours=1):
                    print('yyass -', time_difference)
                    # text_notif.last_send = current_time
                    # text_notif.save()

                    # gotta send the notif to the list of all users that are nearby and has turned on notifications. later we are also gonna use email as notifications but for now gotta use the existing one.
                    all_nearby_usrs = universi.allNearbyUsers.all()
                    for user in all_nearby_usrs:
                       
                        print('the fukin usr - ',user)
                        if user.notif:
                            # here send the notification to this user
                            try:
                                
                                redirect_url=f"{domain_name}/account/{user.pk}/"
                                message=f"Heyy {user.name}, more than {count}+ nearby students are online on text right now wanna join them..."
                                print(message)
                                registration_token = user.ntoken
                                message = messaging.Message(
                                    notification=messaging.Notification(
                                        title='MyStranger.in',
                                        body=message,
                                        # click_action=redirect_url,
                                    ),
                                    data={
                                        'url': redirect_url,
                                        # 'logo': logo_url,
                                    },
                                    token=registration_token,
                                )
                                print('thi is the rediri url -', redirect_url)
                                response = messaging.send(message)

                                print('Successfully sent the friend req msg message:', response)
                            except Exception as e:
                                print('Sendif notif is erroring - ', str(e))

                else:
                    print('nope - ', time_difference)

            except Exception as e:
                print('some excption occured dude while sending 10+ notif- ', str(e))


        return count
    except University.DoesNotExist:
        try:
            count = 0
            universi_prof = UniversityProfile.objects.get(name=uni_name)
            active_video_obj = ActiveVideoUsers.objects.get(pk=1)
            active_users = active_video_obj.users.all()
            nearby_active_users = set()
            for user in active_users:
                if user in universi_prof.allNearbyUsers.all():
                    nearby_active_users.add(user)
                    count += 1

            return count
           
        except UniversityProfile.DoesNotExist:
            print('something went wrong....')

@database_sync_to_async
def create_text_count(user):
    uni_name = user.university_name
    try:
        count = 0
        universi = University.objects.get(name=uni_name)
        active_video_obj = ActiveVideoUsers.objects.get(pk=2)
        active_users = active_video_obj.users.all()
        # nearby_active_users = set()
        for user in active_users:
            if user in universi.allNearbyUsers.all():
                # nearby_active_users.add(user)
                count += 1
        
        if count > 1:
            print('more than 10+ people are online')
            """
            so here we gotta send a notif to all the nearby users of this user that more than 10 are online plus also gotta check that the last notif was sent before one hr to avoid spamming
            """
            try:
                text_notif = Notif.objects.get(pk=2)
                # Get the current time
                current_time = timezone.now()

                # Calculate the time difference
                time_difference = current_time - text_notif.last_send

                # Compare if the time difference is greater than 1 hour
                if time_difference > timedelta(hours=1):
                    print('yyass -', time_difference)
                    # text_notif.last_send = current_time
                    # text_notif.save()

                    # gotta send the notif to the list of all users that are nearby and has turned on notifications. later we are also gonna use email as notifications but for now gotta use the existing one.
                    all_nearby_usrs = universi.allNearbyUsers.all()
                    for user in all_nearby_usrs:
                       
                        print('the fukin usr - ',user)
                        if user.notif:
                            # here send the notification to this user
                            try:
                                
                                redirect_url=f"{domain_name}/account/{user.pk}/"
                                message=f"Heyy {user.name}, more than {count}+ nearby students are online on text right now wanna join them..."
                                print(message)
                                registration_token = user.ntoken
                                message = messaging.Message(
                                    notification=messaging.Notification(
                                        title='MyStranger.in',
                                        body=message,
                                        # click_action=redirect_url,
                                    ),
                                    data={
                                        'url': redirect_url,
                                        # 'logo': logo_url,
                                    },
                                    token=registration_token,
                                )
                                print('thi is the rediri url -', redirect_url)
                                response = messaging.send(message)

                                print('Successfully sent the friend req msg message:', response)
                            except Exception as e:
                                print('Sendif notif is erroring - ', str(e))

                else:
                    print('nope - ', time_difference)

            except Exception as e:
                print('some exception occured dude while sending 10+ notif- ', str(e))

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


@database_sync_to_async
def fetch_active_count():
    try:
        count_obj = ActiveUsers.objects.get(pk=1)
        return count_obj.users.all().count()
    except ActiveUsers.DoesNotExist:
        print('Active users model does not exist!')

@database_sync_to_async
def fetch_total_regs():
    try: 
        count = Account.objects.filter(is_verified = True).count()
        return count
    except Account.DoesNotExist:
        print('Exception in total regs count - ')
        return None