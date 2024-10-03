from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from mystranger_app.models import University , UniversityProfile


class RegisterConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):

        """
        Called when the websocket is handshaking as part of initial connection.
        """

        print('Connect - ')
        await self.accept()

        await self.send_json({
            'connected': 'you are now connected with the consumer'
        },)

    async def receive_json(self, content):

        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """

        command = content.get("command", None)
        print("receive_json: " + str(command))

        try:
            if command == 'email':
                await self.send_info(content["email_address"])
        except Exception as e:
            print(e)

    async def disconnect(self, code):
        pass

    async def send_info(self, email):
        """
        Called by receive_json when someone sends a message to a room.
        """

        # going to write the logic here

        '''
        first we will check that do we have a university associated with that email or not.
        '''
        universityName = None
        lat = None 
        lon = None
        uniprofile = False
        fetched_from = None
        address = None

        print('Everything at None - Just starting')

        try:
            name = email.split('@')[-1:][0]
            university = await fetch_university(name)
            # fetching university from university models
            if university:
                lat = university.lat
                lon = university.lon
                universityName = university.universityName
                address = university.universityAddress
                fetched_from = 0

                print('fetched from - 0 , found on existing universities')
                # print('The address is - ', address, university)
            else:
                '''
                This means that we don't have any university associated with the given email, therefore we are now going to look into our database to check whether we have any university in our database that is associated with this email.
                '''

                universities_database = {
                    "fake_domain.edu": ["Amity University, Greater Noida", 28.54322285, 77.33274829733952,'Amity Address'],
                    # "galgotiasuniversity.edu.in": ["Galgotias University", 28.3671232, 77.54045993787369,'Galgotia Address'],
                    # "bennett.edu.in": ["Bennett University", 28.450610849999997, 77.58391181955102, 'bennet Address'],
                    # "sharda.ac.in": ["Sharda University", 28.4734073, 77.4829339, 'sharda Address'],
                    # "niu.edu.in": ["Noida International University", 28.37390315, 77.54131056418103, 'niu address'],
                    # "cu.edu.in": ["Chandigarh University", 30.7680079, 76.57566052483162, 'cu address'],
                }

                

                try:
                    if name in universities_database:
                        info = universities_database[name]
                        universityName = info[0]
                        address = info[3]
                        lat = info[1]
                        lon = info[2]
                        fetched_from = 2

                        print('Using The Json Database')

                    else: 
                        '''
                        This means that the given university doesn't exist in our database therefore we need to take this university as an input from the user.
                        
                        - but first we are gonna check whether there is a profile for that university or not , and if there are many profiles then the profile with the maximum user is going to get selected.

                        - though we still don't know for sure that whether this profile is true or not. therefore we are going to give user an option saying not my university and by clicking on that user can input their university through search Map.
                        '''

                        university = await fetch_university_profile(name=name)
                        print('looking inside profiles')

                        if university:
                            lat = university.lat
                            lon = university.lon
                            universityName = university.universityName
                            address = university.universityAddress
                            uniprofile = True
                            fetched_from = 1

                        else:
                            print('Only Option is to take user input')
                            fetched_from = 'nope'
                            universityName = 'nope'
                            address = 'nope'
                        
                except Exception as e:
                    print(e)

            await self.send_json(
                {
                    'fetched_from' : fetched_from,
                    'universityName': str(universityName),
                    'universityAddress': str(address),
                    'lat': lat,
                    'lon': lon,
                },
            )

            if uniprofile:
                await self.send_json(
                {
                    'trust_button' : 'Not My University'
                },
            )
        except Exception as e:
            print('This exception is from account consumer',e)


'''
Some Functions to make our life easier.
'''


@database_sync_to_async
def fetch_university(name):
    try:
        university = University.objects.get(name=name)
    except University.DoesNotExist:
        university = None
    return university

'''
This function has to return all the uniprofiles and return the profile which has the maximum users in it.
'''

@database_sync_to_async
def fetch_university_profile(name):
    try:
        university_queryset = UniversityProfile.objects.filter(name=name)
        if university_queryset.exists():
            university_count_dict = {}
            for university in university_queryset:
                # Access and process each university object
                university_count_dict[university] = university.users_count()
            
            max_users_uni = max(university_count_dict, key=university_count_dict.get)
            university = max_users_uni
        else:
            university = None

    except UniversityProfile.DoesNotExist:
        university = None
    return university