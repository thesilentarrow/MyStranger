from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.conf import settings
from mystranger.settings import domain_name
# from CodingWithMitchChat.settings import domain_name
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from chat.utils import find_or_create_private_chat
from notification.models import Notification
from mystranger_app.utils import send_notification_fb
from firebase_admin import messaging


# def send_web_push(registration_token, title, body, url):
#     # Define the webpush configuration
#     webpush_config = messaging.WebpushConfig(
#         notification=messaging.WebpushNotification(
#             title=title,
#             body=body,
#             icon='/images/icon.png'  # Optional
#         )
# 		# ,
#         # fcm_options={
#         #     'link': url
#         # }
#     )

#     # Create the message
#     message = messaging.Message(
#         webpush=webpush_config,
#         token=registration_token
#     )

#     # Send the message
#     response = messaging.send(message)
#     print('Successfully sent message:', response)


# from django.templatetags.static import static
# from django.contrib.sites.models import Site

# # Get the current site
# current_site = Site.objects.get_current()

# # Generate the logo URL
# logo_url = current_site.domain + static('images/msico.ico')


class FriendList(models.Model):

	user 				= models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user")
	friends 			= models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="friends") 

	# set up the reverse relation to GenericForeignKey
	notifications		= GenericRelation(Notification)

	def __str__(self):
		return self.user.name

	def add_friend(self, account):
		"""
		Add a new friend.
		"""
		if not account in self.friends.all():
			self.friends.add(account)
			self.save()

			content_type = ContentType.objects.get_for_model(self)

			self.notifications.create(
				target=self.user,
				from_user=account,
				redirect_url=f"{domain_name}/account/{account.pk}/",
				verb=f"You are now friends with {account.name}.",
				content_type=content_type,
			)
			self.save()
			# send_notification_fb(user_id=id, title="Notification Title", message="Notification message", data=None)

		# Create a private chat (or activate an old one)
			chat = find_or_create_private_chat(self.user, account)
			if not chat.is_active:
				chat.is_active = True
				chat.save()

			

	def remove_friend(self, account):
		"""
		Remove a friend.
		"""
		if account in self.friends.all():
			self.friends.remove(account)
			self.save()
		
		# Deactivate the private chat between these two users
			chat = find_or_create_private_chat(self.user, account)
			if chat.is_active:
				chat.is_active = False
				chat.save()
        
	def unfriend(self, removee):
		"""
		Initiate the action of unfriending someone.
		"""
		remover_friends_list = self # person terminating the friendship

		# Remove friend from remover friend list
		remover_friends_list.remove_friend(removee)

		# Remove friend from removee friend list
		friends_list = FriendList.objects.get(user=removee)
		friends_list.remove_friend(remover_friends_list.user)
		
		content_type = ContentType.objects.get_for_model(self)

		# Create notification for removee
		friends_list.notifications.create(
			target=removee,
			from_user=self.user,
			redirect_url=f"{domain_name}/account/{self.user.pk}/",
			verb=f"You are no longer friends with {self.user.name}.",
			content_type=content_type,
		)

		# Create notification for remover
		self.notifications.create(
			target=self.user,
			from_user=removee,
			redirect_url=f"{domain_name}/account/{removee.pk}/",
			verb=f"You are no longer friends with {removee.name}.",
			content_type=content_type,
		)


	def is_mutual_friend(self, friend):
		"""
		Is this a friend?
		"""
		if friend in self.friends.all():
			return True
		return False
	
	@property
	def get_cname(self):
		"""
		For determining what kind of object is associated with a Notification
		"""
		return "FriendList"

class FriendRequest(models.Model):
	"""
	A friend request consists of two main parts:
		1. SENDER
			- Person sending/initiating the friend request
		2. RECIVER
			- Person receiving the friend friend
	"""

	sender 				= models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sender")
	receiver 			= models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="receiver")

	is_active			= models.BooleanField(blank=False, null=False, default=True)

	timestamp 			= models.DateTimeField(auto_now_add=True)

	notifications		= GenericRelation(Notification)

	def __str__(self):
		return self.sender.name

	def accept(self):
		"""
		Accept a friend request.
		Update both SENDER and RECEIVER friend lists.
		"""
		receiver_friend_list = FriendList.objects.get(user=self.receiver)
		if receiver_friend_list:

			content_type = ContentType.objects.get_for_model(self)

			# Update notification for RECEIVER
			receiver_notification = Notification.objects.get(target=self.receiver, content_type=content_type, object_id=self.id)
			receiver_notification.is_active = False
			receiver_notification.redirect_url = f"{domain_name}/account/{self.sender.pk}/"
			receiver_notification.verb = f"You accepted {self.sender.name}'s friend request."
			receiver_notification.timestamp = timezone.now()
			receiver_notification.save()

			receiver_friend_list.add_friend(self.sender)
			sender_friend_list = FriendList.objects.get(user=self.sender)
			if sender_friend_list:

				# Create notification for SENDER
				self.notifications.create(
					target=self.sender,
					from_user=self.receiver,
					redirect_url=f"{domain_name}/account/{self.receiver.pk}/",
					verb=f"{self.receiver.name} accepted your friend request.",
					content_type=content_type,
				)
				# redirect_url=f"{domain_name}/account/{self.receiver.pk}/"
				# message=f"{self.receiver.name} accepted your friend request."
				# print(message, 'this is the msg')
				# send_notification_fb(
				# 	user_id=self.sender.id,
				# 	title="MyStranger.in",
				# 	message=message,
				# 	data={
				# 		"click_action": redirect_url,  # Replace with your URL
				# 	}
				# )

				# print('sent the accept frnd req-notif')

				# redirect_url=f"{domain_name}/account/{self.receiver.pk}/"
				# message=f"{self.receiver.name} accepted your friend request."
				# registration_token = self.sender.ntoken
				# message = messaging.Message(
				# 	notification=messaging.Notification(
				# 		title='MyStranger.in',
				# 		body=message,
				# 	),
				# 	data={
				# 		'url': redirect_url,
				# 		# 'logo': logo_url,
				# 	},
				# 	token=registration_token,
				# )


				# # Send a message to the device corresponding to the provided
				# # registration token.
				# response = messaging.send(message)
				# print('Successfully sent the accept firend req message:', response)



				sender_friend_list.add_friend(self.receiver)
				self.is_active = False
				self.save()
				
			return receiver_notification # we will need this later to update the realtime notifications
			

	def decline(self):
		"""
		Decline a friend request.
		Is it "declined" by setting the `is_active` field to False
		"""
		self.is_active = False
		self.save()

		content_type = ContentType.objects.get_for_model(self)

		# Update notification for RECEIVER
		notification = Notification.objects.get(target=self.receiver, content_type=content_type, object_id=self.id)
		notification.is_active = False
		notification.redirect_url = f"{domain_name}/account/{self.sender.pk}/"
		# notification.redirect_url = f"#"
		notification.verb = f"You declined {self.sender.name}'s friend request."
		notification.from_user = self.sender
		notification.timestamp = timezone.now()
		notification.save()

		# Create notification for SENDER
		self.notifications.create(
			target=self.sender,
			verb=f"Stranger has declined your friend request.",
			from_user=self.receiver,
			redirect_url=f"#",
			content_type=content_type,
		)

		return notification


	def cancel(self):
		"""
		Cancel a friend request.
		Is it "cancelled" by setting the `is_active` field to False.
		This is only different with respect to "declining" through the notification that is generated.
		"""
		self.is_active = False
		self.save()

		content_type = ContentType.objects.get_for_model(self)

		# Create notification for SENDER
		self.notifications.create(
			target=self.sender,
			verb=f"You cancelled the friend request to sent to the stranger",
			from_user=self.receiver,
			redirect_url=f"#",
			content_type=content_type,
		)

		notification = Notification.objects.get(target=self.receiver, content_type=content_type, object_id=self.id)
		notification.verb = f"Stranger cancelled the friend request sent to you."
		notification.read = False
		notification.save()

		# redirect_url=f"{domain_name}/account/{self.receiver.pk}/"
		# message=f"{self.receiver.name} cancelled your friend request."
		# print(message, 'this is the msg')
		# send_notification_fb(
		# 	user_id=self.sender.id,
		# 	title="MyStranger.in",
		# 	message=message,
		# 	data={
		# 		"click_action": redirect_url,  # Replace with your URL
		# 	}
		# )

		# redirect_url=f"{domain_name}/account/{self.sender.pk}/"
		# message=f"You cancelled the friend request to sent to the stranger"
		# registration_token = self.sender.ntoken
		# message = messaging.Message(
		# 	notification=messaging.Notification(
		# 		title='MyStranger.in',
		# 		body=message,
		# 	),
		# 	data={
		# 		'url': redirect_url,
		# 		# 'logo': logo_url,
		# 	},
		# 	token=registration_token,
		# )

		# response = messaging.send(message)
		# print('Successfully sent the friend req msg message:', response)


		print('cancel the accept frnd req-notif')

	@property
	def get_cname(self):
		"""
		For determining what kind of object is associated with a Notification
		"""
		return "FriendRequest"

@receiver(post_save, sender=FriendRequest)
def create_notification(sender, instance, created, **kwargs):
	if created:
		instance.notifications.create(
			target=instance.receiver,
			from_user=instance.sender,
			redirect_url=f"{domain_name}/account/{instance.sender.pk}/",
			verb=f"{instance.sender.name} sent you a friend request.",
			content_type=instance,
		)

		# redirect_url=f"{domain_name}/account/{instance.sender.pk}/"
		# message=f"{instance.sender.name} sent you a friend request."
		# registration_token = instance.receiver.ntoken
		# message = messaging.Message(
		# 	notification=messaging.Notification(
		# 		title='MyStranger.in',
		# 		body=message,
		# 		# click_action=redirect_url,
		# 	),
		# 	data={
		# 		'url': redirect_url,
		# 		'tag' : 'look',
		# 		'logo': 'static/images/msico.ico',
		# 	},
		# 	token=registration_token,
		# )
		# print('thi is the rediri url with tag - look', redirect_url)
		# response = messaging.send(message)


		

		# print('Successfully sent the friend req msg message:', response)

		
		# Call the function
		# send_web_push(
		# 	registration_token=registration_token,
		# 	title='MyStranger.in',
		# 	body=message,
		# 	url='https://www.mystranger.in/'
		# )

		# redirect_url=f"{domain_name}/account/{instance.sender.pk}/"
		# message=f"{instance.sender.name} sent you a friend request."
		# registration_token = instance.receiver.ntoken
		# # print(message, 'this is the msg')
		# send_notification_fb(
		# 	user_id=instance.sender.id,
		# 	title="MyStranger.in",
		# 	message="mai chutia hu",
		# 	data={
		# 		"click_action": redirect_url,  # Replace with your URL
		# 	}
		# )

		# print('sent the accept frnd req-notif')

		# See documentation on defining a message payload.

		# we gotta fetch the registration token of the person whom we are sending this notif


		# message = messaging.Message(
		# 	notification=messaging.Notification(
		# 		title='MyStranger.in',
		# 		body=message,
		# 	),
		# 	token=registration_token,
		# )

		