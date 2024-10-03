from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.serializers import serialize
from chat.exceptions import ClientError
from django.core.paginator import Paginator
from django.db.models import Q
from itertools import chain

from django.utils import timezone
import json

from chat.models import RoomChatMessage, PrivateChatRoom
from friend.models import FriendList
from account.utils import LazyAccountEncoder
from chat.constants import *
from chat.utils import calculate_timestamp, LazyRoomChatMessageEncoder
from django.utils import timezone
from datetime import timedelta
from firebase_admin import messaging
from mystranger.settings import domain_name

from django.core.serializers.json import DjangoJSONEncoder


class PrivateChatConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        print("ChatConsumer: connect: " + str(self.scope["user"].name))

        # let everyone connect. But limit read/write to authenticated users
        await self.accept()

        # the room_id will define what it means to be "connected". If it is not None, then the user is connected.
        self.room_id = None

    async def receive_json(self, content):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        # Messages will have a "command" key we can switch on
        print("ChatConsumer: receive_json")
        command = content.get("command", None)
        try:
            if command == "join":
                print("joining room: " + str(content['room']))
                await self.join_room(content["room"])

            elif command == "leave":
                # Leave the room
                await self.leave_room(content["room"])
            elif command == "send":
                if len(content["message"].lstrip()) != 0:
                    await self.send_room(content["room"], content["message"], content['rep_msg'], content['rep_name'],content['rep_id'])
            elif command == 'typing':
                await self.send_typing(content['group_name'], content['userId'])
            elif command == "status_check":
                print('status_check command recieved : ')
                await self.status_check_service()
            elif command == "delete_message":
                print('wow delete msg command is called! ')
                room = await get_room_or_error(content['room_id'], self.scope["user"])
                await self.delete_message_service(room,content['sender_id'], content['msg_id'])
            elif command == "get_room_chat_messages":
                await self.display_progress_bar(True)
                room = await get_room_or_error(content['room_id'], self.scope["user"])
                payload = await get_room_chat_messages(room, content['page_number'])
                if payload != None:
                    payload = json.loads(payload)
                    await self.send_messages_payload(payload['messages'], payload['new_page_number'])
                else:
                    raise ClientError(
                        204, "Something went wrong retrieving the chatroom messages.")
                await self.display_progress_bar(False)
            elif command == "get_user_info":
                await self.display_progress_bar(True)
                room = await get_room_or_error(content['room_id'], self.scope["user"])
                payload = get_user_info(room, self.scope["user"])
                if payload != None:
                    payload = json.loads(payload)
                    await self.send_user_info_payload(payload['user_info'])
                else:
                    raise ClientError(204,
                        "Something went wrong retrieving the other users account details.")
                await self.display_progress_bar(False)

            

            elif command == "mark_room_read":
                print('marking the messages as red for room - ',
                      content['room_id'])
                await mark_room_read(self.scope["user"], content['room_id'])
                await self.send_json({
                    "marked": 'true',
                })
        except ClientError as e:
            await self.display_progress_bar(False)
            await self.handle_client_error(e)

    async def disconnect(self, code):
        """
        Called when the WebSocket closes for any reason.
        """
        # Leave the room
        print("ChatConsumer: disconnect")
        try:
            if self.room_id != None:
                await self.leave_room(self.room_id)
        except ClientError as e:
            print("EXCEPTION: " + str(e))
            await self.handle_client_error(e)
            

    async def join_room(self, room_id):
        """
        Called by receive_json when someone sent a join command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware (AuthMiddlewareStack)
        print("ChatConsumer: join_room: " + str(room_id))
        try:
            room = await get_room_or_error(room_id, self.scope["user"])
        except ClientError as e:
            return await self.handle_client_error(e)

        # Store that we're in the room
        self.room_id = room.id
        group_name = room.group_name
        # Add them to the group so they get room messages
        await self.channel_layer.group_add(
            room.group_name,
            self.channel_name,
        )

        # room.connected_users.add(self.scope['user'])
        # room.save()
        Added = await Add_or_remove_from_room(True, room, self.scope['user'])

        other_user_last_seen = await other_persons_last_seen(room,self.scope['user'])
        print('bro did i got the timestamp - ', other_user_last_seen)

        # Instruct their client to finish opening the room
        await self.send_json({
            "join": str(room.id),
            "room_name" : group_name,
            'room_id' : str(room.id),
            'last_seen': json.dumps(other_user_last_seen, cls=DjangoJSONEncoder),
        })

        count = await connected_users_count(room)
        print("_______________________ The count is ---------------", count)
        if count > 1:
            status = "online"
        else:
            status = "offline"

        

        if self.scope["user"].is_authenticated:
            # Notify the group that someone joined
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "chat.join",
                    "room_id": room_id,
                    "room_name":group_name,
                    "uniName": self.scope["user"].university_name,
                    "name": self.scope["user"].name,
                    "user_id": self.scope["user"].id,
                    "status" : status,
                    
                }
            )

    async def leave_room(self, room_id):
        """
        Called by receive_json when someone sent a leave command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        print("ChatConsumer: leave_room")

        room = await get_room_or_error(room_id, self.scope["user"])
        await mark_room_read(self.scope["user"], room_id)

        try:
            Removed = await Add_or_remove_from_room(False,room,self.scope['user'])
            print(Removed)
        except ClientError as e:
            print('Exception during removing user from room.connected_users')
            Removed = await Add_or_remove_from_room(False,room,self.scope['user'])
            return await self.handle_client_error(e)

        

        # Notify the group that someone left
        try:
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "chat.leave",
                    "room_id": room_id,
                    "uniName": self.scope["user"].university_name,
                    "name": self.scope["user"].name,
                    "user_id": self.scope["user"].id,
                    
                }
            )
        except ClientError as e:
            print('Exception during sending leave chat msg to group - ', str(e))

        print("******* The leave chat msg is sent! **********")

        # try:
        #     await self.channel_layer.group_send(
        #         room.group_name,
        #         {
        #             "type": "chat.leave",
        #             "room_id": room_id,
        #             "uniName": self.scope["user"].university_name,
        #             "name": self.scope["user"].name,
        #             "user_id": self.scope["user"].id,
                    
        #         }
        #     )
        # except Exception as e:
        #     print('Exception during sending leave chat msg to group - ', str(e))

        # print("******* The leave chat msg is sent AGAIN! **********")
        

        # Remove that we're in the room
        self.room_id = None

        # Remove them from the group so they no longer get room messages
        await self.channel_layer.group_discard(
            room.group_name,
            self.channel_name,
        )
        # try:
        #     Removed = await Add_or_remove_from_room(False,room,self.scope['user'])
        #     print(Removed)
        # except Exception as e:
        #     print('Exception during removing user from room.connected_users Again!!')
        #     Removed = await Add_or_remove_from_room(False,room,self.scope['user'])
        # Instruct their client to finish closing the room
        await self.send_json({
            "leave": str(room.id),
        })

    async def send_room(self, room_id, message,rep_msg,rep_name,rep_id):
        """
        Called by receive_json when someone sends a message to a room.
        """
        print("ChatConsumer: send_room")
        # Check they are in this room
        if self.room_id != None:
            if str(room_id) != str(self.room_id):
                raise ClientError("ROOM_ACCESS_DENIED",
                                  "Room access denied")
        else:
            raise ClientError("ROOM_ACCESS_DENIED",
                              "Room access denied")

        # Get the room and send to the group about it
        room = await get_room_or_error(room_id, self.scope["user"])

        count = await connected_users_count(room)
        if count > 1:
            # This means the jerk is online so messages sent are marked as read
            print('The connected_user_count is - ', count, " so marking msg as read")
            msg = await create_room_chat_message(room, self.scope["user"], message, True,rep_msg,rep_name,rep_id)
            read = True
            if msg.parent == "":
                print('This is not a fuckin reply')
                parenti = 'Noneee'
                parenti_name = "null",
                parenti_id = 'null',
            else:
                print('this is indeed a fuckin reply')
                parenti = msg.parent
                parenti_name = msg.parent_name
                parenti_id = msg.parent_id
        else:
            # This means the jerk is onffline so messages sent are marked as unread
            print('The connected_user_count is - ', count, " so marking msg as unread")
            msg = await create_room_chat_message(room, self.scope["user"], message, False,rep_msg,rep_name,rep_id)
            read = False
            if msg.parent == "":
                print('This is not a fuckin reply')
                parenti = 'Noneee'
                parenti_name = "null",
                parenti_id = 'null',
            else:
                print('this is indeed a fuckin reply')
                parenti = msg.parent
                parenti_name = msg.parent_name
                parenti_id = msg.parent_id

        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "chat.message",
                "uniName": self.scope["user"].university_name,
                "name": self.scope["user"].name,
                "user_id": self.scope["user"].id,
                "message": message,
                "read" : read,
                "msg_id" : msg.id,
                'reply_msg': parenti,
                "reply_name":parenti_name,
                'reply_id': parenti_id
            }
        )

    # These helper methods are named by the types we send - so chat.join becomes chat_join

    async def chat_join(self, event):
        """
        Called when someone has joined our chat.
        """
        
        # Send a message down to the client
        print("ChatConsumer: chat_join: " + str(self.scope["user"].id))
        if event["name"]:
            await self.send_json(
                {
                    "msg_type": MSG_TYPE_ENTER,
                    "room": event["room_id"],
                    "room_name": event["room_name"],
                    "uniName": event["uniName"],
                    "name": event["name"],
                    "user_id": event["user_id"],
                    "message": event["name"] + " connected.",
                    'status' : event['status'],
                    
                },
            )

    async def chat_leave(self, event):
        """
        Called when someone has left our chat.
        """
        # Send a message down to the client
        print("ChatConsumer: chat_leave")
        if event["name"]:
            await self.send_json(
                {
                    "msg_type": MSG_TYPE_LEAVE,
                    "room": event["room_id"],
                    "uniName": event["uniName"],
                    "name": event["name"],
                    "user_id": event["user_id"],
                    "message": event["name"] + " disconnected.",
                },
            )

    async def chat_message(self, event):
        """
        Called when someone has messaged our chat.
        """
        # Send a message down to the client
        print("ChatConsumer: chat_message")

        timestamp = calculate_timestamp(timezone.now())

        await self.send_json(
            {
                "msg_type": MSG_TYPE_MESSAGE,
                "name": event["name"],
                "user_id": event["user_id"],
                "uniName": event["uniName"],
                "message": event["message"],
                "read": event["read"],
                "natural_timestamp": timestamp,
                'msg_id' : event['msg_id'],
                'reply_msg':event['reply_msg'],
                'reply_name':event['reply_name'],
                'reply_id':event['reply_id'],
            },
        )

    async def status_check_service(self):

        try:
            room_id = self.room_id
            room = await get_room_or_error(room_id, self.scope["user"])
        except ClientError as e:
            return await self.handle_client_error(e)
        
        count = await connected_users_count(room)
        print("_______________________ The count is ---------------", count)
        if count > 1:
            status = "online"
        else:
            status = "offline"

        if self.scope["user"].is_authenticated:
            # Notify the group that someone joined
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "status.check",
                    "room_id": room_id,
                    'status_check' : 'checking_status',
                    "status" : status,
                    # "uniName": self.scope["user"].university_name,
                    # "name": self.scope["user"].name,
                    # "user_id": self.scope["user"].id,
                }
            )

    
    async def status_check(self, event):
        
        # Send a message down to the client
        print("ChatConsumer: status_check: " + str(self.scope["user"].id))
        await self.send_json(
            {
                "status_check": event['status_check'],
                "status": event['status'],
                "room_id": event["room_id"],
            }, 
        )
        


    async def send_typing(self, group_name,userId):
        """
        Called by receive_json when someone starts typing a message to a room.
        """
        print("-----------  typing  ---------------\n")
        print(userId," is typing a message.\n")
        await self.channel_layer.group_send(
            str(group_name),
            {
                'type': 'user.typing',
                'isTyping' : True,
                # 'username': userName,
                'id' : userId,
            }
        )

    async def delete_message_service(self, room , sender_id, msg_id):

        
        # call a func that deletes the message
        deleted = await del_msg(room,sender_id,msg_id)
        
        if self.scope["user"].is_authenticated:
            # Notify the group that someone joined
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "msgdel.message",
                    'deleted' : 'True',
                    "deleter_id" : sender_id,
                    "msg_id" : msg_id,
                    
                }
            )
        
    async def msgdel_message(self, event):
    
        # Send a message down to the client
        print("ChatConsumer: status_check: " + str(self.scope["user"].id))
        await self.send_json(
            {
                "message_deleted": event['deleted'],
                "deleter_id": event['deleter_id'],
                "msg_id": event["msg_id"],
            }, 
        )


    async def user_typing(self, event):
        # Send the "user is typing" message to the recipient user
        await self.send_json(
            {
            'isTyping': event['isTyping'],
            # 'username': event['username'],
            'id' : event['id'],
        }
        )


    async def send_messages_payload(self, messages, new_page_number):
        """
        Send a payload of messages to the ui
        """
        print("ChatConsumer: send_messages_payload. ")
        await self.send_json(
            {
                "messages_payload": "messages_payload",
                "messages": messages,
                "new_page_number": new_page_number,
            },
        )

    async def send_user_info_payload(self, user_info):
        """
        Send a payload of user information to the ui
        """
        print("ChatConsumer: send_user_info_payload. ")
        await self.send_json(
            {
                "user_info": user_info,
            },
        )

    async def display_progress_bar(self, is_displayed):
        """
        1. is_displayed = True
                - Display the progress bar on UI
        2. is_displayed = False
                - Hide the progress bar on UI
        """
        print("DISPLAY PROGRESS BAR: " + str(is_displayed))
        await self.send_json(
            {
                "display_progress_bar": is_displayed
            }
        )

    async def handle_client_error(self, e):
        """
        Called when a ClientError is raised.
        Sends error data to UI.
        """
        errorData = {}
        errorData['error'] = e.code
        if e.message:
            errorData['message'] = e.message
            await self.send_json(errorData)
        return

    


@database_sync_to_async
def get_room_or_error(room_id, user):
    """
    Tries to fetch a room for the user, checking permissions along the way.
    """
    try:
        room = PrivateChatRoom.objects.get(pk=room_id)
    except PrivateChatRoom.DoesNotExist:
        raise ClientError("Invalid room.","room doesn't exist")

    # Is this user allowed in the room? (must be user1 or user2)
    if user != room.user1 and user != room.user2:
        raise ClientError("Permission Denied","You do not have permission to join this room.")

    # Are the users in this room friends?
    friend_list = FriendList.objects.get(user=user).friends.all()
    if not room.user1 in friend_list:
        if not room.user2 in friend_list:
            raise ClientError("Not Friends","You must be friends to chat.")
    return room

# I don't think this requires @database_sync_to_async since we are just accessing a model field
# https://docs.djangoproject.com/en/3.1/ref/models/instances/#refreshing-objects-from-database


def get_user_info(room, user):
    """
    Retrieve the user info for the user you are chatting with
    """
    try:
        # Determine who is who
        other_user = room.user1
        if other_user == user:
            other_user = room.user2

        payload = {}
        s = LazyAccountEncoder()
        # convert to list for serializer and select first entry (there will be only 1)
        payload['user_info'] = s.serialize([other_user])[0]
        return json.dumps(payload)
    except ClientError as e:
        print("EXCEPTION: " + str(e))

    print("none I guess?...")
    return None


@database_sync_to_async
def create_room_chat_message(room, user, message, read,rep_msg, rep_name,rep_id):
    rekage = message
    try:
        pass
        # if read == False:
        #     # This means the user is not online, now first we gotta check that whether i have received a message from this user within the past 10 minutes or not, if not then create a notification.

        #     # in order to do that we gotta fetch all the messages sent by that user to me within 10 minutes

        #     if room.user1 == user:
        #         friend = room.user2
        #     else:
        #         friend = room.user1

        #     # unread_messages = RoomChatMessage.objects.filter(
        #     #     Q(room=room) & Q(user=friend) & Q(read=False))

        #     # Get the current time
        #     now = timezone.now()

        #     # Calculate the time 10 minutes ago
        #     ten_minutes_ago = now - timedelta(minutes=10)

        #     # Fetch the messages
        #     messages = RoomChatMessage.objects.filter(
        #         user=user,
        #         room=room,
        #         timestamp__gte=ten_minutes_ago
        #     )

        #     if messages.exists():
        #         print("There are messages in the past 10 minutes so do nothing.")

        #     else:
        #         print("There are no messages in the past 10 minutes. so send a notification to the current user")
        #         redirect_url=f"{domain_name}/chat/"
        #         messagei=f"{user.name} sent you a message"
        #         registration_token = friend.ntoken
        #         message = messaging.Message(
        #             notification=messaging.Notification(
        #                 title='MyStranger.in',
        #                 body=messagei,
        #                 # click_action=redirect_url,
        #             ),
        #             data={
        #                 'url': redirect_url,
        #                 # 'tag' : 'look',
        #                 'logo': 'static/images/msico.ico',
        #             },
        #             token=registration_token,
        #         )
        #         print('thi is the rediri url with tag - look', redirect_url)
        #         response = messaging.send(message)


        #         print('Successfully sent the  msg message notif:', response)

    except Exception as e:
        print('error creating message notification - ', str(e))
        
    print('got the rep_msg - ', rep_msg)
    if rep_msg or rep_name:
        print('reply msg')
        return RoomChatMessage.objects.create(user=user, room=room, content=rekage, read=read, parent=rep_msg, parent_name=rep_name,parent_id=rep_id)
    else:
        print('normal msg')
        return RoomChatMessage.objects.create(user=user, room=room, content=rekage, read=read)


@database_sync_to_async
def get_room_chat_messages(room, page_number):
    try:
        qs = RoomChatMessage.objects.by_room(room)
        p = Paginator(qs, DEFAULT_ROOM_CHAT_MESSAGE_PAGE_SIZE)

        payload = {}
        messages_data = None
        new_page_number = int(page_number)
        if new_page_number <= p.num_pages:
            new_page_number = new_page_number + 1
            s = LazyRoomChatMessageEncoder()
            payload['messages'] = s.serialize(p.page(page_number).object_list)
        else:
            payload['messages'] = "None"
        payload['new_page_number'] = new_page_number
        return json.dumps(payload)
    except Exception as e:
        print("EXCEPTION: " + str(e))
        return None




@database_sync_to_async
def mark_room_read(user, room_id):
    """
    marks all the message send by friend to me as "read"
    """
    if user.is_authenticated:

        room = PrivateChatRoom.objects.filter(id=room_id).first()
        if room.user1 == user:
            friend = room.user2
        else:
            friend = room.user1
        unread_messages = RoomChatMessage.objects.filter(
            Q(room=room) & Q(user=friend) & Q(read=False))
        if unread_messages:
            for message in unread_messages:
                message.read = True
                message.save()

    return

@database_sync_to_async
def Add_or_remove_from_room(Boolean, room,user):
    if Boolean:
        users = room.connected_users.all()
        print('***********************')
        print('users - ', users)
        print(user not in users)
        if user not in users:
            room.connected_users.add(user)
            room.save()
    else:
        users = room.connected_users.all()
        print("%%%%%%%%%%%%%%%%")
        print('users - ', users)
        print(user in users)
        if user in users:
            room.connected_users.remove(user)
            room.save()
        print("%%%%%%%%%%%%%%%%")
        print('users - ', room.connected_users.all())
    return True

@database_sync_to_async
def connected_users_count(room):
    count = room.connected_users.all().count()
    return count

@database_sync_to_async
def other_persons_last_seen(room,user):
    last_seen = None
    try:
        if room.user1 == user:
            last_seen = room.user2.last_activity
        else: 
            last_seen = room.user1.last_activity

    except Exception as e:
        print('fuck')
    return last_seen

@database_sync_to_async
def del_msg(room,sender_id,msg_id):
    deleted = False
    try:
        msg_del = RoomChatMessage.objects.filter(id=msg_id,room=room).delete()
        deleted = True

    except Exception as e:
        print('fuck')

    return deleted
