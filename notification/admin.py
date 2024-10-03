from django.contrib import admin


from notification.models import Notification
from notification.models import ActiveUsers
from notification.models import ActiveVideoUsers
from notification.models import Notif

class NotificationAdmin(admin.ModelAdmin):
    list_filter = ['content_type',]
    list_display = ['target', 'content_type', 'timestamp']
    search_fields = ['target__username',]
    readonly_fields = []

    class Meta:
        model = Notification


admin.site.register(Notification, NotificationAdmin)
admin.site.register(ActiveUsers)
admin.site.register(ActiveVideoUsers)
admin.site.register(Notif)