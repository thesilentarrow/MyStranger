from django.contrib import admin
from django.contrib import admin
from django.core.paginator import Paginator
from django.core.cache import cache

from nrt.models import NrtPrivateChatRoom, NrtRoomChatMessage, AllActivatedUsers , Meetup , MeetupConnection, NrtIceBreakers

class NrtPrivateChatRoomAdmin(admin.ModelAdmin):
	list_display = ['id','user1', 'user2', 'created_at' ]
	search_fields = ['id', 'user1__name', 'user2__name','user1__email', 'user2__email', ]
	readonly_fields = ['id',]

	class Meta:
		model = NrtPrivateChatRoom


admin.site.register(NrtPrivateChatRoom, NrtPrivateChatRoomAdmin)


# Resource: http://masnun.rocks/2017/03/20/django-admin-expensive-count-all-queries/
# class CachingPaginator(Paginator):
# 	def _get_count(self):
# 		if not hasattr(self, "_count"):
# 			self._count = None
# 		if self._count is None:
# 			try:
# 				key = "adm:{0}:count".format(hash(self.object_list.query.__str__()))
# 				self._count = cache.get(key, -1)
# 				if self._count == -1:
# 					self._count = super().count
# 					cache.set(key, self._count, 3600)
# 			except:
# 				self._count = len(self.object_list)
# 			return self._count

# 	count = property(_get_count)


class NrtRoomChatMessageAdmin(admin.ModelAdmin):
	list_filter = ['room',  'user', "timestamp"]
	list_display = ['room',  'user', 'content',"timestamp"]
	search_fields = ['user__name','user__email','content']
	readonly_fields = ['id', "user", "room", "timestamp"]

	# show_full_result_count = False
	# paginator = CachingPaginator

	class Meta:
		model = NrtRoomChatMessage


admin.site.register(NrtRoomChatMessage, NrtRoomChatMessageAdmin)
admin.site.register(AllActivatedUsers)
admin.site.register(Meetup)
admin.site.register(MeetupConnection)
admin.site.register(NrtIceBreakers)