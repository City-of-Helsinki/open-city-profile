from django.contrib import admin

from profiles.models import Profile


class ProfileAdmin(admin.StackedInline):
    model = Profile
