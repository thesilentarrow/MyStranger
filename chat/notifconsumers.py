from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from account.models import Account
from chat.models import RoomChatMessage, PrivateChatRoom
from django.db.models import Q
from itertools import chain
import json

class PrivateChatNotificationConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        print("ChatNotificationConsumer: connect: " + str(self.scope["user"]))
        await self.accept()

    async def disconnect(self, code):
        """
        Called when the WebSocket closes for any reason.
        """
        print("ChatNotificationConsumer: disconnect")

    async def receive_json(self, content):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        command = content.get("command", None)
        print("ChatNotificationConsumer: receive_json. Command: " + command)

        try:
            if command == "start":
                payload = await unread_msg_count(content['friends_dict'],self.scope['user'])
                if payload == None:
                    print(payload,'Payload does not exist')
                else:
                    payload = json.loads(payload)
                    await self.unread_msg_count_payload(payload)

        except Exception as e:
            print("EXCEPTION: receive_json: " + str(e))
            pass

    async def unread_msg_count_payload(self,payload):
         
         await self.send_json(
            {
                "receive_unread_msg_count": 'async_unread_msg_count',
                "payload_dict": payload,
            },
        )

@database_sync_to_async
def unread_msg_count(friends_dict,user):
    # print(friends_dict,type(friends_dict))
    id_unread_msg_dict = {}
    for id in friends_dict.values():
        # print('The id is -', id)
        friend = Account.objects.filter(id=id, is_verified = True).first()
        # print("friend is - " , friend)
        if friend:
            # This means here we have both friend and user
    
            try: 
                room = PrivateChatRoom.objects.get(Q(user1=user) & Q(user2=friend) & Q(is_active=True))
            except:
                room = PrivateChatRoom.objects.filter(Q(user1=friend) & Q(user2=user) & Q(is_active=True)).first()
            # print(room, user)
            unread_messages_count = RoomChatMessage.objects.filter(Q(room=room) & Q(user=friend) & Q(read = False)).count()
            # print(id , unread_messages_count)
            id_unread_msg_dict[id] = unread_messages_count
            
    # print(id_unread_msg_dict)
    return json.dumps(id_unread_msg_dict)
