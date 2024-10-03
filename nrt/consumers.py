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

from nrt.models import NrtPrivateChatRoom, NrtRoomChatMessage , Meetup , NrtIceBreakers
from datetime import datetime
import random



class NrtPrivateChatConsumer(AsyncJsonWebsocketConsumer):

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
            elif command == "req_meetup":
                print('req meetup is called - ', content['gender'], content['id'])
                await self.send_meetup_req(content['gender'],content['id'],content['room'], content['address'], content['date'],content['time'])

            # elif command == "cancel_meetup":
            #     print('cancel meetup is called - ', content['gender'], content['id'])
            #     await self.send_cancel_meetup_req(content['gender'],content['id'],content['room'])
            elif command == "fix_meetup":
                print('fix meetup is called - ', content['gender'], content['id'], content['address'], content['date'],content['time'])
                await self.fix_meetup_req(content['gender'],content['id'],content['room'], content['address'], content['date'],content['time'])
            elif command == "send":
                if len(content["message"].lstrip()) != 0:
                    await self.send_room(content["room"], content["message"])
            elif command == 'typing':
                await self.send_typing(content['group_name'], content['userId'])
            elif command == "status_check":
                print('status_check command recieved : ')
                await self.status_check_service()
            elif command == "delete_message":
                print('wow delete msg command is called! ')
                room = await get_room_or_error(content['room_id'], self.scope["user"])
                await self.delete_message_service(room,content['sender_id'], content['msg_id'])
            elif command == "change_ice":
                print('wow change_ice command is called! ')
                room = await get_room_or_error(content['room'], self.scope["user"])
                await self.change_icebreaker(room,content['id'])
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
            # pass
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

        # Instruct their client to finish opening the room
        await self.send_json({
            "join": str(room.id),
            "room_name" : group_name,
            'room_id' : str(room.id),
        })

        count = await connected_users_count(room)
        print("_______________________ The count is ---------------", count)
        if count > 1:
            status = "online"
        else:
            status = "offline"

        perci = await meetup_percentage(room, self.scope['user'])

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
                    "perci" : perci,
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


    async def send_room(self, room_id, message):
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
            msg = await create_room_chat_message(room, self.scope["user"], message, True)
            read = True
        else:
            # This means the jerk is onffline so messages sent are marked as unread
            print('The connected_user_count is - ', count, " so marking msg as unread")
            msg = await create_room_chat_message(room, self.scope["user"], message, False)
            read = False


        # now we gotta fuckin calculate the percentage right -
        perci = await meetup_percentage(room,self.scope['user'])

        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "chat.message",
                "uniName": self.scope["user"].university_name,
                "name": self.scope["user"].name,
                "user_id": self.scope["user"].id,
                "message": message,
                "read" : read,
                'perci' : perci,
                "msg_id" : msg.id,
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
                    'percentage' : event['perci'],
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
                'percentage' : event['perci'],
                "msg_id" : event['msg_id'],
            },
        )

    async def send_meetup_req(self, gender, sender_id, room,address,date,time):

        # Get the room and send to the group about it
        roomva = await get_room_or_error(room, self.scope["user"])

        if gender == 'M':
            '''
            Here we have to create a meetup request
            '''

            meetup_requa = await meetup_request(self.scope['user'], True, sender_id, roomva, False,None,None,None)

        elif gender == 'F':
            meetup_requa = await meetup_request(self.scope['user'], False, sender_id, roomva, False, address, date, time)

        print('are we reaching this point or not')

        

        await self.channel_layer.group_send(
            roomva.group_name,
            {
                "type": "req.message",
                "date_req":'date_req',
                "user_id":sender_id,
                'req_created': 'True',
                'gender':gender,
                'address' : address,
                'date' : date,
                'time' : time,
                
            }
        )

        

    async def req_message(self, event):

        print('where is the error')

        await self.send_json(
            {
                "date_req":event['date_req'],
                "user_id":event['user_id'],
                'req_created': event['req_created'],
                'gender':event['gender'],
                'address' : event['address'],
                'date' : event['date'],
                'time' : event['time'],
            },
        )

    # async def send_cancel_meetup_req(self, gender, sender_id, room):

    #     # Get the room and send to the group about it
    #     roomva = await get_room_or_error(room, self.scope["user"])

    #     meetup_requa = await cancel_meetup_request(self.scope['user'], sender_id, roomva)
        

    #     print('are we reaching this cancel req point or not')

    #     await self.channel_layer.group_send(
    #         roomva.group_name,
    #         {
    #             "type": "cancel_req.message",
    #             "req_cancelled":'date_cancelled',
    #             "user_id":sender_id,
    #             'gender':gender,
                
    #         }
    #     )

        

    # async def cancel_req_message(self, event):

    #     print('where is the error')

    #     await self.send_json(
    #         {
    #             "req_cancelled":event['req_cancelled'],
    #             "user_id":event['user_id'],
    #             'gender':event['gender'],
    #         },
    #     )

    async def fix_meetup_req(self, gender, sender_id, room, address, date, time):

        print('fix meetup is called')

        # Get the room and send to the group about it
        roomva = await get_room_or_error(room, self.scope["user"])

        if gender == 'M':
            '''
            Here we have to create a meetup request
            '''

            meetup_requa = await meetup_request(self.scope['user'], True, sender_id, roomva, True, None, None, None)

        elif gender == 'F':
            fix_meetupva = await meetup_request(self.scope['user'], False, sender_id, roomva, True,address, date, time)

        print('are we reaching this point or not')

        await self.channel_layer.group_send(
            roomva.group_name,
            {
                "type": "fix.req.message",
                "date_fixed":'date_fixed',
                "user_id":sender_id,
                'req_created': 'True',
                'gender':gender,
                'address' : address,
                'date' : date,
                'time' : time,
                
            }
        )

        

    async def fix_req_message(self, event):

        print('where is the error')

        await self.send_json(
            {
                "date_fixed":event['date_fixed'],
                "user_id":event['user_id'],
                'req_created': event['req_created'],
                'gender':event['gender'],
                'address' : event['address'],
                'date' : event['date'],
                'time' : event['time'],
            },
        )

    async def status_check_service(self):

        try:
            room_id = self.room_id
            room = await get_room_or_error(room_id, self.scope["user"])
        except ClientError as e:
            return await self.handle_client_error(e)
        
        count = await connected_users_count(room)
        # print("_______________________ The count is ---------------", count)
        if count > 1:
            status = "online"
        else:
            status = "offline"

        # if room.user1 == self.scope["user"]:
        #     last_seen = room.user2.last_activity
        # else:
        #     last_seen = room.user1.last_activity

        # last_seen = int(last_seen)

        if self.scope["user"].is_authenticated:
            # Notify the group that someone joined
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "status.check",
                    "room_id": room_id,
                    'status_check' : 'checking_status',
                    "status" : status,
                    # "last_seen" : last_seen,
                    # "uniName": self.scope["user"].university_name,
                    # "name": self.scope["user"].name,
                    # "user_id": self.scope["user"].id,
                }
            )

    async def status_check(self, event):
        
        # Send a message down to the client
        # print("ChatConsumer: status_check: " + str(self.scope["user"].id))
        await self.send_json(
            {
                "status_check": event['status_check'],
                "status": event['status'],
                # "last_seen" : event['last_seen'],
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

    async def change_icebreaker(self, room , id):

        
        # call a func that changes the icebreaker
        iceque = await change_icebreaker(room)
        
        
        
        if self.scope["user"].is_authenticated:
            # Notify the group that someone joined
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "changeice.message",
                    'ice_changed' : 'yes',
                    'ice_ques' : iceque
                    
                }
            )
        
    async def changeice_message(self, event):
    
        # Send a message down to the client
        print("ChatConsumer: status_check: " + str(self.scope["user"].id))
        await self.send_json(
            {
                "ice_changed": event['ice_changed'],
                "ice_ques": event['ice_ques'],
                
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

    # async def send_user_info_payload(self, user_info):
    #     """
    #     Send a payload of user information to the ui
    #     """
    #     print("ChatConsumer: send_user_info_payload. ")
    #     await self.send_json(
    #         {
    #             "user_info": user_info,
    #         },
    #     )


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
        room = NrtPrivateChatRoom.objects.get(pk=room_id)
    except NrtPrivateChatRoom.DoesNotExist:
        raise ClientError("Invalid room.","Other user has cancelled the date")

    # Is this user allowed in the room? (must be user1 or user2)
    if user != room.user1 and user != room.user2:
        raise ClientError("Permission Denied","You do not have permission to join this room.")

    return room


@database_sync_to_async
def create_room_chat_message(room, user, message, read):
    rekage = message
    try:
        if read == False:
            # This means the user is not online, now first we gotta check that whether i have received a message from this user within the past 10 minutes or not, if not then create a notification.

            # in order to do that we gotta fetch all the messages sent by that user to me within 10 minutes

            if room.user1 == user:
                friend = room.user2
            else:
                friend = room.user1

            # unread_messages = RoomChatMessage.objects.filter(
            #     Q(room=room) & Q(user=friend) & Q(read=False))

            # Get the current time
            now = timezone.now()

            # Calculate the time 10 minutes ago
            ten_minutes_ago = now - timedelta(minutes=10)

            # Fetch the messages
            messages = NrtRoomChatMessage.objects.filter(
                user=user,
                room=room,
                timestamp__gte=ten_minutes_ago
            )

            if messages.exists():
                print("There are messages in the past 10 minutes so do nothing.")

            else:
                print("There are no messages in the past 10 minutes. so send a notification to the current user")
                redirect_url=f"{domain_name}/chat/"
                messagei=f"{user.name} sent you a message"
                registration_token = friend.ntoken
                message = messaging.Message(
                    notification=messaging.Notification(
                        title='MyStranger.in',
                        body=messagei,
                        # click_action=redirect_url,
                    ),
                    data={
                        'url': redirect_url,
                        # 'tag' : 'look',
                        'logo': 'static/images/msico.ico',
                    },
                    token=registration_token,
                )
                print('thi is the rediri url with tag - look', redirect_url)
                response = messaging.send(message)


                print('Successfully sent the  msg message notif:', response)

    except Exception as e:
        print('error creating message notification - ', str(e))
        

    return NrtRoomChatMessage.objects.create(user=user, room=room, content=rekage, read=read)


@database_sync_to_async
def get_room_chat_messages(room, page_number):
    try:
        qs = NrtRoomChatMessage.objects.by_room(room)
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

        room = NrtPrivateChatRoom.objects.filter(id=room_id).first()
        if room.user1 == user:
            friend = room.user2
        else:
            friend = room.user1
        unread_messages = NrtRoomChatMessage.objects.filter(
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

@database_sync_to_async
def meetup_request(user, gender , id, roomva, fixing, address, date, time):

    meetup_req = None

    
    try:
        if not fixing:
            '''
            Here one user has requested another user for a meetup so if thats a male he can just send a req but if its a female she can send a req and also send the address and time of the meetup, than its upto the other user whether they wanna accept the meetup or not.
            '''
            if gender:
                print('male has requested a meetup')
                meetup_req = Meetup.objects.filter(Q(user1=user) | Q(user2=user)).first()
                if meetup_req:
                    pass
                else:
                    meetup_req = Meetup(user1=user, room=roomva)
                    meetup_req.save()
            else:
                print('a fe fuckin male ahm female has requested a meetup')
                meetup_req = Meetup.objects.filter(Q(user1=user) | Q(user2=user)).first()
                if meetup_req:
                    pass
                else:
                    

                    # Convert date and time strings to Python datetime objects
                    datetime_str = f"{date} {time}"
                    datetime_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                    meetup_req = Meetup(user2=user, room=roomva, address1=address, datetime=datetime_obj)
                    meetup_req.save()

        else:
            if not gender:
                print('yeah i am a wonan fixin a date')
                # This means the fuckin women is now fixing the date
                meetup_req = Meetup.objects.filter(Q(user1=user) | Q(user2=user)).first()
                if not meetup_req:
                    # Convert date and time strings to Python datetime objects
                    datetime_str = f"{date} {time}"
                    datetime_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                    meetup_req = Meetup.objects.filter(room=roomva).first()
                    if meetup_req:
                        meetup_req.address1 = address
                        if meetup_req.user1:
                            meetup_req.user2 = user
                        elif meetup_req.user2:
                            meetup_req.user1 = user
                        meetup_req.datetime = datetime_obj
                        meetup_req.is_fixed = True
                        meetup_req.save()

                        # This means the date is fixed so create a record that a new offline date is fixed
            else:
                print('fuckin male is fixin a date')
                meetup_req = Meetup.objects.filter(Q(user1=user) | Q(user2=user)).first()
                if not meetup_req:
                    meetup_req = Meetup.objects.filter(room=roomva).first()
                    if meetup_req:
                        if meetup_req.user1:
                            meetup_req.user2 = user
                        elif meetup_req.user2:
                            meetup_req.user1 = user
                        meetup_req.is_fixed = True
                        meetup_req.save()
                        
                        # This means the date is fixed so create a record that a new offline date is fixed

    except Exception as e:
        meetup_req = None
        print('some exception at meetup_request section - ', str(e))
    
    return meetup_req




# @database_sync_to_async
# def cancel_meetup_request(user, sender_id, roomva):

#     cancel_meetup_req = None

#     try:

#         meetup_req = Meetup.objects.filter(Q(user1=user) | Q(user2=user) | Q(room=roomva)).first()
#         print(sender_id, user.id, 'are bc', str(sender_id) == str(user.id))
#         if meetup_req and (str(sender_id) == str(user.id)):
#             meetup_req.delete()
            
#         meetup_req = True
#     except Exception as e:
#         meetup_req = None
#         print('some exception at meetup_request section - ', str(e))
    
#     return meetup_req


@database_sync_to_async
def del_msg(room,sender_id,msg_id):
    deleted = False
    try:
        msg_del = NrtRoomChatMessage.objects.filter(id=msg_id,room=room).delete()
        deleted = True

    except Exception as e:
        print('fuck')

    return deleted


@database_sync_to_async
def change_icebreaker(room):
    icebreakers = NrtIceBreakers.objects.all()
    if icebreakers:
        random_question = random.choice(icebreakers)
        try:
            nrt_room = NrtPrivateChatRoom.objects.get(id=room.id)
            print('so this is the nrt_room - ', nrt_room.icebreaker)
            nrt_room.icebreaker = random_question.question
            nrt_room.save()
        except NrtPrivateChatRoom.DoesNotExist:
            # Handle the case when the object doesn't exist
            print('paji no room existo')

        return random_question.question
    return None