from django.db import models
from django.conf import settings
from mptt.models import MPTTModel, TreeForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver
from notification.models import Notification
from mystranger.settings import domain_name
from django.db.models.signals import m2m_changed
from firebase_admin import messaging


class CPublicChatRoom(models.Model):

	# Room title
	title 				= models.CharField(max_length=255, unique=False, blank=False,)
	question			= models.CharField(max_length=10005, unique=False, blank=False,)
	owner               = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='CPublicChatRoom')
	taggie               = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='CPublicChatRoomTaggie', null=True, blank=True)
	timestamp           = models.DateTimeField(auto_now_add=True)
	confesserid			= models.CharField(max_length=105, unique=False, blank=False)
	taggie_token			= models.CharField(max_length=2005, unique=False, blank=True, null=True)
	taggie_email			= models.CharField(max_length=105, unique=False, blank=True, null=True)
	taggie_name			= models.CharField(max_length=105, unique=False, blank=True, null=True)
	taggie_link			= models.CharField(max_length=405, unique=False, blank=True, null=True)
	taggie_info			= models.CharField(max_length=2005, unique=False, blank=True, null=True)
	is_sent = models.BooleanField(default=False)
	is_tagged = models.BooleanField(default=False)
	
	
	


	

	# all users who are authenticated and viewing the chat
	users 				= models.ManyToManyField(settings.AUTH_USER_MODEL, help_text="users who are connected to chat room.")

	def __str__(self):
		return self.question

	def ans_count(self):
		return self.Canswers.filter(parent=None).count()
	
	# def poll_count(self):
	# 	polls = self.polls.filter(question=self)
	# 	count = 0
	# 	for poll in polls:
	# 		count += poll.polled.all().count()
	# 	return count

	def connect_user(self, user):
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


	def disconnect_user(self, user):
		"""
		return true if user is removed from the users list
		"""
		is_user_removed = False
		if user in self.users.all():
			self.users.remove(user)
			self.save()
			is_user_removed = True
		return is_user_removed 
	
	# def is_already_polled(self,user):
	# 	for poll in self.polls.all():
	# 		if user in poll.polled.all():
	# 			return True
	# 	return False


	@property
	def group_name(self):
		"""
		Returns the Channels Group name that sockets should subscribe to to get sent
		messages as they are generated.
		"""
		return self.question


class CPublicRoomChatMessageManager(models.Manager):
    def by_room(self, room):
        qs = CPublicRoomChatMessage.objects.filter(room=room).order_by("-timestamp")
        return qs

class CPublicRoomChatMessage(models.Model):
    """
    Chat message created by a user inside a PublicChatRoom
    """
    user                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room                = models.ForeignKey(CPublicChatRoom, on_delete=models.CASCADE)
    timestamp           = models.DateTimeField(auto_now_add=True)
    content             = models.TextField(unique=False, blank=False,)
    emoji = models.CharField(max_length=2)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True)

    objects = CPublicRoomChatMessageManager()

    def __str__(self):
        return self.content


class CAnswer(MPTTModel):
	question            = models.ForeignKey(CPublicChatRoom, on_delete=models.CASCADE, related_name='Canswers')
	user                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	content             = models.TextField(unique=False, blank=False,)
	# parent  			= models.ForeignKey('self',on_delete=models.CASCADE, null=True)
	parent = TreeForeignKey('self', on_delete=models.CASCADE,
                            null=True, blank=True, related_name='Cchildren')
	timestamp 			= models.DateTimeField(auto_now_add=True)
	likes				= models.ManyToManyField(settings.AUTH_USER_MODEL, help_text="Likes", blank=True, related_name='Clikes')
	ans_reports				= models.ManyToManyField(settings.AUTH_USER_MODEL, help_text="Reports", blank=True, related_name='Cans_reports')
	is_like_action = models.BooleanField(default=False, editable=False)
	is_report_action = models.BooleanField(default=False, editable=False)
	confesserid			= models.CharField(max_length=105, unique=False, blank=False, null=True)


	# set up the reverse relation to GenericForeignKey
	notifications		= GenericRelation(Notification)

	class MPTTMeta:
		order_insertion_by = ['timestamp']

	def add_like(self, user):
		"""
		return true if user is added to the users list
		"""
		is_user_added = False
		if not user in self.likes.all():
			self.likes.add(user)
			self.save()
			is_user_added = True
		elif user in self.likes.all():
			is_user_added = True
		return is_user_added 


	def remove_like(self, user):
		"""
		return true if user is removed from the users list
		"""
		is_user_removed = False
		if user in self.likes.all():
			self.likes.remove(user)
			self.save()
			is_user_removed = True
		return is_user_removed 
	
	def add_flag(self, user):
		"""
		return true if user is added to the users list
		"""
		is_user_added = False
		if not user in self.ans_reports.all():
			self.ans_reports.add(user)
			self.save()
			is_user_added = True
		elif user in self.ans_reports.all():
			is_user_added = True
		return is_user_added 


	def remove_flag(self, user):
		"""
		return true if user is removed from the users list
		"""
		is_user_removed = False
		if user in self.ans_reports.all():
			self.ans_reports.remove(user)
			self.save()
			is_user_removed = True
		return is_user_removed 


	def __str__(self):
		return self.content
	
	@property
	def get_cname(self):
		"""
		For determining what kind of object is associated with a Notification
		"""
		return "CAnswer"

@receiver(post_save, sender=CAnswer)
def create_notification(sender, instance, **kwargs):

	# Check if the instance was saved due to a like action
	if instance.is_like_action:
		
		# find a way to notify users if someone likes their answer
				
		return 
	
	if instance.is_report_action:
		
		# find a way to notify users if someone likes their answer
				
		return 

	
	if instance.parent:
		# print(instance.parent, 'this tis the fuckin parent')
		if instance.parent.user != instance.user:
			if instance.user == instance.question.taggie:
				name = 'Receiver'
			else:
				name="Stranger"
			instance.notifications.create(
				target=instance.parent.user,
				from_user=instance.user,
				redirect_url=f"{domain_name}/confessions/question/{instance.id}/",
				verb=f"{name} replied this at your confession - {instance.content[:50]} ..." if len(instance.content) > 50 else f"{name} replied this at your Confession - {instance.content}",
				content_type=instance,
			)
			try:
				redirect_url=f"{domain_name}/account/{instance.parent.user.pk}/"
				message=f"{name} replied this at your confession - {instance.content[:50]} ..." if len(instance.content) > 50 else f"{name} replied this at your Confession - {instance.content}"
				registration_token = instance.parent.user.ntoken
				message = messaging.Message(
					notification=messaging.Notification(
						title='MyStranger.in',
						body=message,
						# click_action=redirect_url,
					),
					data={
						'url': redirect_url,
						'logo': "static\images\msico.ico",
					},
					token=registration_token,
				)
				print('thi is the rediri url -', redirect_url)
				response = messaging.send(message)


				

				print('Successfully sent the friend req msg message:', response)
			except Exception as e:
				print('error notifio - ', str(e))
	else:
		if instance.user != instance.question.owner:
			if instance.user == instance.question.taggie:
				name = 'Receiver'
			else:
				name="Stranger"
			instance.notifications.create(
				target=instance.question.owner,
				from_user=instance.user,
				redirect_url=f"{domain_name}/confessions/question/{instance.id}/",
				# verb=f"{instance.user.name} Answered at your question",
				verb=f"{name} said this at your confession - {instance.content[:50]} ..." if len(instance.content) > 50 else f"{name} said this at your Confession - {instance.content}",
				content_type=instance,
			)

			try:
				redirect_url=f"{domain_name}/account/{instance.question.owner}/"
				message=f"{name} said this at your confession - {instance.content[:50]} ..." if len(instance.content) > 50 else f"{name} said this at your Confession - {instance.content}"
				registration_token = instance.question.owner.ntoken
				message = messaging.Message(
					notification=messaging.Notification(
						title='MyStranger.in',
						body=message,
						# click_action=redirect_url,
					),
					data={
						'url': redirect_url,
						'logo': "static\images\msico.ico",
					},
					token=registration_token,
				)
				print('thi is the rediri url -', redirect_url)
				response = messaging.send(message)


				

				print('Successfully sent the friend req msg message:', response)
			except Exception as e:
				print('error notif - ', str(e))
		
		


# Signal handler to set is_like_action to True when likes are changed
@receiver(m2m_changed, sender=CAnswer.likes.through)
def update_is_like_action(sender, instance, action, **kwargs):
    if action == 'post_add' or action == 'post_remove':
        instance.is_like_action = True
        instance.save()

# Signal handler to set is_like_action to True when likes are changed
@receiver(m2m_changed, sender=CAnswer.ans_reports.through)
def update_is_report_action(sender, instance, action, **kwargs):
    if action == 'post_add' or action == 'post_remove':
        instance.is_report_action = True
        instance.save()


