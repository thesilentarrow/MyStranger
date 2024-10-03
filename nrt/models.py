from django.db import models
from django.conf import settings

# Create your models here.

class NrtPrivateChatRoom(models.Model):

    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nrt_user1')
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nrt_user2')
    icebreaker			= models.CharField(max_length=2005, unique=False, blank=False, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    connected_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="nrt_connected_users")

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'A Chat between {self.user1.name} and {self.user2.name}.'

    @property
    def group_name(self):
        """
		Returns the Channels Group name that sockets should subscribe to to get sent
		messages as they are generated.
		"""
        return f'NrtPrivateChatRoom-{self.id}'


class NrtRoomChatMessageManager(models.Manager):
    def by_room(self,room):
        qs = NrtRoomChatMessage.objects.filter(room=room).order_by('-timestamp')
        return qs

class NrtRoomChatMessage(models.Model):
    """
	Chat message created by a user inside a Room
	"""
    user                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room                = models.ForeignKey(NrtPrivateChatRoom, on_delete=models.CASCADE)
    timestamp           = models.DateTimeField(auto_now_add=True)
    content             = models.TextField(unique=False, blank=False,)
    parent             = models.TextField(unique=False,null=True, blank=True)
    parent_name             = models.TextField(unique=False,null=True, blank=True)
    parent_id             = models.TextField(unique=False,null=True, blank=True)
    read 						= models.BooleanField(default=False)

    objects = NrtRoomChatMessageManager()

    def __str__(self):
        return self.content
    

class AllActivatedUsers(models.Model):

    users = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name=("all-activated-list"), blank=True)

    def add_user(self, user):
        """
        return true if user is added to the users list
        """
        is_user_added = False
        if not user in self.users.all():
            self.users.add(user)
            self.save()
            is_user_added = True
        elif user in self.users.all():
            is_user_added = True
        return is_user_added 


    def remove_user(self, user):
        """
        return true if user is removed from the users list
        """
        is_user_removed = False
        if user in self.users.all():
            self.users.remove(user)
            self.save()
            is_user_removed = True
        return is_user_removed 

    def __str__(self):
        return f'all activated list - {self.users.all().count()}'

class Meetup(models.Model):
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meetup_user1', null=True)
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meetup_user2', null=True)
    room                = models.ForeignKey(NrtPrivateChatRoom, on_delete=models.CASCADE)

    lat = models.FloatField(blank=False, null=True)
    lon = models.FloatField(blank=False, null = True)
    datetime = models.DateTimeField(blank=True, null=True)

    address1		= models.CharField(max_length=5005, unique=False,blank=True, null=True)
    address2		= models.CharField(max_length=5005, unique=False,blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_fixed						= models.BooleanField(default=False)


    def __str__(self):
        return f'Date between {self.user1} and {self.user2}'

class MeetupConnection(models.Model):
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='initiated_connections', on_delete=models.CASCADE)
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_connections', on_delete=models.CASCADE)
    connection_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')
    
    def __str__(self):
        return f'connection between {self.user1} and {self.user2} at {self.connection_time}'

class NrtIceBreakers(models.Model):
    question			= models.CharField(max_length=2005, unique=False, blank=False,)
    timestamp           = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question