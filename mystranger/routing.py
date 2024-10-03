from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path, re_path
from mystranger.asgi import get_asgi_application
django_asgi_app = get_asgi_application()
from mystranger_app.consumers import ChatConsumer
from mystranger_app.consumers2 import ChatConsumerText
from account.consumers import RegisterConsumer
from chat.consumers import PrivateChatConsumer 
from chat.notifconsumers import PrivateChatNotificationConsumer
from notification.consumers import NotificationConsumer
from qna.consumers import PublicChatConsumer
from nrt.consumers import NrtPrivateChatConsumer

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
	'websocket': AllowedHostsOriginValidator(
		AuthMiddlewareStack(
			URLRouter([
				
				path('chat/', ChatConsumer.as_asgi()),
				path('chat_text/', ChatConsumerText.as_asgi()),
                path('nrtchat/<room_id>/', NrtPrivateChatConsumer.as_asgi()),
				path('register/', RegisterConsumer.as_asgi()),
				path('mchat/<eoom_id>/', PrivateChatConsumer.as_asgi()),
                path('public_chat/<room_id>/', PublicChatConsumer.as_asgi()),
				path('mchat-notif/', PrivateChatNotificationConsumer.as_asgi()),
                path('', NotificationConsumer.as_asgi()),
				
				]
				
			)
		)
	),
})