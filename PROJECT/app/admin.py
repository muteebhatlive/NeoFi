from django.contrib import admin

# Register your models here.

from .models import UserProfile

# Register the UserProfile model with the admin site
admin.site.register(UserProfile)