from channels.generic.websocket import AsyncJsonWebsocketConsumer
from mystranger_app.utils import generateOTP
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from mystranger_app.models import WaitingArea, GroupConnect, Profile, University, UniversityProfile
from django.db.models import Q
import random
import json
import asyncio
from channels.layers import get_channel_layer


class ChatConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):

        """
        Called when the websocket is handshaking as part of initial connection.
        """

        print('Connect - ')
        await self.accept()

        # Here we are defining some essential instance variables
        self.id = None
        self.group_name = None
        self.origin = None

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
                print("Trying to join a chat - ")
                await self.join_room(self.scope['user'])

            # elif command == 'grouped':
            #     self.group_name = content['group_name']
            #     print(
            #         f'instance variable self.group_name has been set for {self.id} ')

            elif command == 'offer':
                await self.channel_layer.group_send(content['group'], {
                    'type': 'offer.message',
                    'offer': content['offer']
                })
            elif command == 'answer':
                await self.channel_layer.group_send(content['group'], {
                    'type': 'answer.message',
                    'answer': content['answer']
                })
            elif(content['command'] == 'candidate'):
                await self.channel_layer.group_send(content['group'], {
                    'type': 'candidate.message',
                    'candidate': content['candidate'],
                    'iscreated': content['iscreated']
                })

        except Exception as e:
            print('The exception - ', str(e))

    async def disconnect(self, code):
        """
        Called when the WebSocket closes for any reason.
        """
        # Leave the room
        print("ChatConsumer: disconnect")
        try:
            await self.leave_room()
        except Exception as e:
            print("Disconnect EXCEPTION: " + str(e))

    async def join_room(self, user):
        """
        Called by receive_json when someone sent a join command.
        """

        # first we have to create a user_profile for this user
        user1 = await create_user(self.channel_name, user)
        print("The channel name is - ", self.channel_name)
        user1_channel = user1.channel_name

        '''
        This is important to identify who has send a command to the front-end from the back-end.
        '''
        self.id = user1.id
        self.origin = user.origin

        # Sending this id to the front-end so that we can use it further.

        await self.send_json(
            {
                "my_id": self.id,
            },
        )

        '''
        fetching the waiting area to check whether there is another request availlable or not
        '''

        university = user.university_name
        count, users = await fetching_waiting_list_count(university, self.origin, user)

        print("----------------------------------")
        print(f'the count is - {count}')

        if count != None and count != 0:
            print('yes another request is availlable')

            await self.send_json(
                {
                    "status_user1": self.id,
                    'user_id': self.id,
                },
            )

            # fetching random user from the set of availlable strangers and then removing that lucky stranger from the waiting list
            random_user = user_random(users)
            is_removed = await removing_user_from_waiting_list(random_user, self.origin)

            if is_removed:
                print('-----------------------------------------')
                print(
                    f'random user has been selected (random_user_id : {random_user}) and thus also removed from the waiting list.')
                random_user_channel = random_user.channel_name

                '''
                now we have two users availlable , user1_self who is seeking to connect with a stranger, user2_random who was patiently waiting in the waiting list to get connected with a stranger.
                Now we have to create a group with these two users so that they can chat with each other.
                '''

                group_name = await create_group(user1, random_user)

                if group_name:
                    self.group_name = group_name
                    print(f'model group is created! {group_name}')

                    # Adding user1 to a group named group_name

                    # try:
                    #     await self.channel_layer.group_add(
                    #         str(group_name),
                    #         self.channel_name
                    #     )
                    # except Exception as e:
                    #     print(
                    #         f'Execption in adding the users to the group - {e} ')

                    # await self.channel_layer.send(random_user_channel, {
                    #     "type": "random.send",
                    #     'group_name' : group_name,
                    #     'random_user_id' : random_user.id,
                    # })

                    # Use asyncio to ensure that adding the user to the group is non-blocking.
                    await asyncio.gather(
                        self.channel_layer.send(
                            random_user_channel,
                            {
                                "type": "random.send",
                                'group_name': group_name,
                                # 'random_user_id' : random_user.id,
                            }
                        ),
                        self.channel_layer.group_add(
                            str(group_name),
                            self.channel_name
                        ),
                    )

                    print('user1 is added to the group - ', group_name)
                    print("Fetchers channel name - ", self.channel_name)
                    print('group name to random_user')

        elif (count == 0 or count == None):
            '''
            here this means that either the waiting list doesn't exist or there is no one in the waiting list , eitherway we have to add this user to the waitingg area
            '''

            print(
                'adding user to the waiting area by fetching or creating the waiting area.')
            waiting_list = await create_waiting_list_and_add_user(user1, self.origin)

            await self.send_json(
                {
                    'satus': "waiting",
                    "status_user2": self.id,
                    'response': 'wait till someone connects with you',
                },
            )

        else:
            print('There is some problem with the waiting list users count.')

    # async def add_user_to_group(self, group_name):
    #     try:
    #         await self.channel_layer.group_add(
    #             str(group_name),
    #             self.channel_name
    #         )
    #         print(f'User {self.channel_name} added to group {group_name}')
    #     except Exception as e:
    #         print(f'Exception in adding the user to the group - {e}')

    # async def send_message_to_other_consumer(self, random_user_channel, group_name):
    #     try:
    #         print('sending group name to the random user through channel')

    #         await self.channel_layer.send(
    #             random_user_channel,
    #             {
    #                 "type": "random.send",
    #                 'group_name': group_name,
    #                 # 'random_user_id' : random_user.id,
    #             }
    #         )
    #     except Exception as e:
    #         print(f'Exception in sending message to the group - {e}')

    async def leave_room(self):
        """
        Called by receive_json when someone sent a leave command.
        """
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        print("ChatConsumer: leave_room")
        print('The group name is - ', self.group_name)
        group_name = self.group_name

        if (self.group_name != None):
            # This means that the user is indeed inside a group

            """
            First we'll notify by sending a msg into the group that the group has been discarded
            """
            print("sending a leave msg to the group")
            try:
                # print("self.group_name - ",self.group_name)
                # print(type(str(self.group_name)))
                # print("self.id - ", self.id)
                await self.channel_layer.group_send(
                    str(self.group_name),
                    {
                        "type": "leave.message",
                        'group_leave': 'Chat Disconnected',
                        # 'by_skip': 'normal',
                        # 'disconnector': self.id,
                        'response': 'You are no longer connected with the stranger.',
                    }
                )
                print("the leave msg is sent to the group")
            except Exception as e:
                print("The send leave msg to group exception - ", str(e))
                
            # Discarding User1 from the group
            print(f'Discarding user from the group.')
            print("The channel name is - ", self.channel_name)
            await self.channel_layer.group_discard(
                str(self.group_name),
                str(self.channel_name)
            )

            # Deleting User1
            print(f'deleting the user - {self.id}')
            user_deleted = await delete_user(self.id)
            print(f'Status : ' + str(user_deleted))

            # Now last but not the least setting the variables back to default
            self.id = None
            self.group_name = None
            self.origin = None

        else:
            # Poor guy is not in any group
            '''
            This means that there is no group formed and the user is simply trying to skip without creating a group. Therefore we just have to delete this user and by deleting it , the user is also automatically gonna get removed from the waiting list.
            '''

            print(f'user - {self.id} deleted!')
            await self.send_json(
                {
                    'solo_leave': 'Chat Disconnected',
                    'disconnector': self.id,
                    'response': 'You are no longer connected with the stranger.',
                },
            )

            delete_user_self = await delete_user(self.id)
            print(f'Status : {delete_user_self}')

            # Now last but not the least setting the variables back to default
            self.id = None
            self.group_name = None
            self.origin = None

    async def leave_message(self, event):
        await self.send_json(
            {
                "group_leave": event['group_leave'],
                # 'by_skip': event['by_skip'],
                # 'disconnector': event['disconnector'],
                "response": event["response"],

            },
        )

    async def random_send(self, event):
        # This method is called when a message is received.
        group_name = event["group_name"]
        self.group_name = group_name

        print('received the group_name baby - ', self.group_name)
        print("The waiters channel name is - ", self.channel_name)
        try:
            await self.channel_layer.group_add(
                str(group_name),
                self.channel_name,
            )
        except Exception as e:
            print(
                f'Execption in adding the users to the group - {e} ')

            print('random_user has been added to the group - ', group_name)

        '''
        At this point both the users has been added to the group_name, so now we have to send a group_msg to notify both the users that they are now connected
        '''

        print('sending message on the group to notify both the users')

        try:
            await self.channel_layer.group_send(
                str(group_name),
                {
                    "type": "joined.room",
                    "grouped": group_name,
                    # "user1_self": user1.id,
                    # 'random_user': random_user.id,
                    # 'user1_self_name' : user1_self_name,
                    # 'random_user_name' : random_user_name,
                    'response': 'You are now connected with a stranger.',
                }
            )
        except Exception as e:
            print(f'Execption in sending msg to the group - {e} ')

        print('group send message has been sent!')

    async def joined_room(self, event):

        content = event['response']
        print('message send to the group - ', content)

        await self.send_json(
            {
                "grouped": event['grouped'],
                # "user1": event["user1_self"],
                # "user1_self_name": event["user1_self_name"],
                # "random_user_name": event["random_user_name"],
                # "random_user": event["random_user"],
                "response": event["response"],
            },
        )

    # --------------------------------------------------------------------------------

    async def offer_message(self, event):
        await self.send_json({
            'command': 'offer',
            'offer': event['offer']
        })

    async def answer_message(self, event):
        await self.send_json({
            'command': 'answer',
            'answer': event['answer']
        })

    async def candidate_message(self, event):
        await self.send_json({
            'command': 'candidate',
            'candidate': event['candidate'],
            'iscreated': event['iscreated']
        })


'''
Creating a User with username as channel_layer of that user and pk is a random 8 digit code to make the user_id unique. 
'''


@database_sync_to_async
def create_user(channel_name, user):
    id = generateOTP()
    channel = channel_name
    user = user
    profile = Profile(id=id, channel_name=channel, user=user)
    profile.save()
    return profile


@database_sync_to_async
def delete_user(id):
    try:
        profile = Profile.objects.get(id=id)
        profile.delete()
        deleted = True
    except:
        deleted = False
    return deleted


'''
Here we are adding the user to the waiting list by either creating the waiting list or by fetching the existimg waiting list.
'''


@database_sync_to_async
def create_waiting_list_and_add_user(user, origin):

    if origin:
        try:
            waiting_list = WaitingArea.objects.get(pk=1)
            if waiting_list:
                is_added = waiting_list.add_user(user)
        except:
            waiting_list = WaitingArea.objects.create(pk=1)
            is_added = waiting_list.add_user(user)
    else:
        try:
            waiting_list = WaitingArea.objects.get(pk=2)
            if waiting_list:
                is_added = waiting_list.add_user(user)
        except:
            waiting_list = WaitingArea.objects.create(pk=2)
            is_added = waiting_list.add_user(user)
    return is_added


def user_random(setva):
    random_user = random.choice(list(setva))
    return random_user


'''
simple function to remove a user from the waiting list.
'''


@database_sync_to_async
def removing_user_from_waiting_list(user, origin):

    try:
        if origin:
            # This means we are dealing with users of origin
            waiting_list = WaitingArea.objects.get(pk=1)
            if waiting_list:
                is_removed = waiting_list.remove_user(user)
        else:
            waiting_list = WaitingArea.objects.get(pk=2)
            if waiting_list:
                is_removed = waiting_list.remove_user(user)
    except WaitingArea.DoesNotExist:
        waiting_list = None
    return is_removed


'''
simple function to create a group of two users.
'''


@database_sync_to_async
def create_group(user1, user2):
    group_name = GroupConnect.objects.create(user1=user1, user2=user2)
    return str(group_name)


'''
here we are fetching the waiting list , assuming that it has already been created with pk equals to 1, 
after that we are returning the count of all the users present in the waiting list to make sure that the list isn't empty.
'''


@database_sync_to_async
def fetching_waiting_list_count(university_name, origin, auth_user):

    # try:
    #     waiting_list = WaitingArea.objects.get(pk=1)
    #     # need some work
    #     # users = waiting_list.users.filter(user__university_name=university_name)
    #     users = waiting_list.users.all()
    #     if waiting_list and users:
    #         count = users.count()
    #     else:
    #         count = 0
    # except:
    #     count = 0

    try:
        count = None
        if origin:
            # This means we are dealing with users of origin
            waiting_list = WaitingArea.objects.get(pk=1)
            waiting_list_nearby = WaitingArea.objects.get(pk=2)
            users_nearby = waiting_list_nearby.users.filter(
                user__university_name=university_name)
            set1 = set(users_nearby)

            # we need the count of all the users from origin that are from his university
            users = waiting_list.users.filter(
                user__university_name=university_name)
            set2 = set(users)
            if waiting_list and (users.exists() or users_nearby.exists()):
                count1 = users.count()
                count2 = users_nearby.count()
                count = count1 + count2
            set3 = set1.union(set2)
            # payload = {'count' : count, 'users' : list(users)}
            # return json.dumps(payload)
            print("The Origin count ------", count)
            print("The set ------", set3)
            return count, set3
        else:

            waiting_list = WaitingArea.objects.get(pk=2)

            # we need the count of all the users from origin that are from his university plus all the users from wl that are in his nearby_list
            waiting_list_origin = WaitingArea.objects.get(pk=1)
            users = waiting_list_origin.users.filter(
                user__university_name=university_name)
            print(users)
            users_nearby = waiting_list.users.filter(
                user__university_name=university_name)
            print(users_nearby)
            set1_1 = set(users)
            print("set 1_1 -------", set1_1)
            set1_2 = set(users_nearby)
            print("set 1_2 -------", set1_2)
            set1 = set1_1.union(set1_2)
            print("set 1 -------", set1)
            all_nearby_users = University.objects.none()
            try:
                university = University.objects.get(name=university_name)
                print('Uni exists so no profile dwelling')
                nearby_universities = university.nearbyList.all()
                print("These are the nearby universities list - ",
                      nearby_universities)

                # --------------------------------------------------------------------------------------------
                # right now if a user with uni_prof is here then it can only connect with others by fetching the other user but other users can't fetch him so if he is in the waiting list then he is not going to get connected with anyone and that's how it is , although we can fix that by adding all_nearby_users_from_profiles but we are not going to do that.

                for universiti in nearby_universities:
                    all_nearby_users |= universiti.users.filter(is_verified = True)

                # all_nearby_users = list(all_nearby_users)
                all_nearby_users_list = []
                for obj in all_nearby_users:
                    all_nearby_users_list.append(obj.email)

                # for obj in all_nearby_users_list:
                #     print(obj)
                #     if 'himanshu.20scse1010435@galgotiasuniversity.edu.in' == obj.email:
                #         print('Yup true')
                #     else:
                #         print('Sup false')
                # if 'himanshu.20scse1010435@galgotiasuniversity.edu.in' in all_nearby_users_list:
                #     print('yes you fuckin hell')
                print("All nearby users -----", all_nearby_users_list)

                nearby_waiting_list_users = waiting_list.users.all()
                print('These are all the nearby waiting list users - ',
                      nearby_waiting_list_users)
                set2 = set()
                for user in nearby_waiting_list_users:
                    print("user from nwlu - ", user.user.email,
                          type(user.user.email))
                    if user.user.email in all_nearby_users_list:
                        print("Yes this brat is in the all_nearby_users", user.user)
                        set2.add(user)
            except University.DoesNotExist:
                print('Uni does not exist so profile dwelling')

                university_prof = UniversityProfile.objects.filter(
                    Q(name=university_name) & Q(users=auth_user)).first()
                print('The university profile is ---------', university_prof)

                nearby_universities = university_prof.nearbyList.all()
                print("These are the nearby universities list - ",
                      nearby_universities)

                for universiti in nearby_universities:
                    all_nearby_users |= universiti.users.filter(is_verified = True)

                all_nearby_users_list = []
                for obj in all_nearby_users:
                    all_nearby_users_list.append(obj.email)

                print("All nearby users -----", all_nearby_users_list)

                nearby_waiting_list_users = waiting_list.users.all()
                print('These are all the nearby waiting list users - ',
                      nearby_waiting_list_users)
                set2 = set()

                for user in nearby_waiting_list_users:
                    if user.user.email in all_nearby_users_list:
                        print("Yes this brat is in the all_nearby_users", user.user)
                        set2.add(user)

            print("Set2 ------------", set2)
            set3 = set1.union(set2)
            print("Set3 ------------", set3)
            if waiting_list and (len(set3) != 0):
                count = len(set3)
            # payload = {'count':count,'users' : list(set3)}
            # return json.dumps(payload)
            print("The Nearby count ------", count)
            print("The set ------", set3)
            return count, set3

    # except WaitingArea.DoesNotExist:
    except Exception as e:
        print("The fucking exception in count - ", str(e))
        # payload = {'count' : None,'users':None}
        count = None
        set3 = None
    print("The default count ----", count)
    print("The set ------", set3)
    return count, set3
