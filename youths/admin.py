from django.contrib import admin

from youths.models import YouthProfile


class YouthProfileAdminInline(admin.StackedInline):
    model = YouthProfile
