from django.db import models
from django.conf import settings


# Create your models here.

class PrivateChatRoom(models.Model):

    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user1')
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user2')

    connected_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="connected_users")

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'A Chat between {self.user1.name} and {self.user2.name}.'

    @property
    def group_name(self):
        """
		Returns the Channels Group name that sockets should subscribe to to get sent
		messages as they are generated.
		"""
        return f'PrivateChatRoom-{self.id}'


class RoomChatMessageManager(models.Manager):
    def by_room(self,room):
        qs = RoomChatMessage.objects.filter(room=room).order_by('-timestamp')
        return qs

class RoomChatMessage(models.Model):
    """
	Chat message created by a user inside a Room
	"""
    user                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room                = models.ForeignKey(PrivateChatRoom, on_delete=models.CASCADE)
    timestamp           = models.DateTimeField(auto_now_add=True)
    content             = models.TextField(unique=False, blank=False,)
    parent             = models.TextField(unique=False,null=True, blank=True)
    parent_name             = models.TextField(unique=False,null=True, blank=True)
    parent_id             = models.TextField(unique=False,null=True, blank=True)
    read 						= models.BooleanField(default=False)

    objects = RoomChatMessageManager()

    def __str__(self):
        return self.content

