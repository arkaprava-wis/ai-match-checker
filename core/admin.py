from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(User)
admin.site.register(Role)
admin.site.register(Franchise)

admin.site.register(State)
admin.site.register(District)
