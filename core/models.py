from django.db import models
import re
# Create your models here.
from django.shortcuts import render
from .managers import UserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.contrib.auth.models import AbstractUser
from django.db.models import Sum
from django.apps import apps


WEST_BENGAL_DISTRICTS = (
    ('Alipurduar', 'Alipurduar'),
    ('Bankura', 'Bankura'),
    ('Birbhum', 'Birbhum'),
    ('Cooch Behar', 'Cooch Behar'),
    ('Dakshin Dinajpur', 'Dakshin Dinajpur'),
    ('Darjeeling', 'Darjeeling'),
    ('Hooghly', 'Hooghly'),
    ('Howrah', 'Howrah'),
    ('Jalpaiguri', 'Jalpaiguri'),
    ('Kalimpong', 'Kalimpong'),
    ('Kolkata', 'Kolkata'),
    ('Nadia', 'Nadia'),
    ('Burdwan','burdwan'),
    ('North 24 Parganas', 'North 24 Parganas'),
    ('Paschim Medinipur', 'Paschim Medinipur'),
    ('Purba Medinipur', 'Purba Medinipur'),
    ('Murshidabad', 'Murshidabad'),
    ('Purulia', 'Purulia'),
    ('South 24 Parganas', 'South 24 Parganas'),
)


class State(models.Model):
    name= models.CharField(
        max_length=100,
        verbose_name=_('state Name'),
    )
    def __str__(self) -> str:
        return self.name
    
class District(models.Model):
    ref_state=models.ForeignKey(State,related_name='districts',on_delete=models.PROTECT)
    name= models.CharField(max_length=500)
    
    def __str__(self) -> str:
        return self.name

class User(AbstractUser):

    first_name = models.CharField(
        max_length=50,
        verbose_name=_('First Name'),
    )

    last_name = models.CharField(
        max_length=50,
        verbose_name=_('Last Name'),
    )

    email = models.EmailField(
        verbose_name=_('Email Address'),
        max_length=150,
        unique=True,
        error_messages={'unique': _('A user with that email already exists.')},
        help_text=_(
            'Required. 150 characters or fewer. Letters, digits and @/./_ only.'
        ),
    )
     # New fields for designation and mobile number.
    designation = models.CharField(
        max_length=100,
        verbose_name=_('Designation'),
        blank=True,
        null=True,
        help_text=_('Enter your designation (e.g., Manager, Developer, etc.).')
    )
    mobile_number = models.CharField(
        max_length=20,
        verbose_name=_('Mobile Number'),
        blank=True,
        null=True,
        help_text=_('Enter your mobile phone number.')
    )

    # EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    # removes email from REQUIRED_FIELDS
    REQUIRED_FIELDS = ['first_name', 'last_name']

    # Custome User Manager
    manager = UserManager()
    objects = UserManager()

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ('-date_joined',)

    def __str__(self) -> str:
        return f'{self.email}'.lower()

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.title()

    @property
    def joined_date(self):
        return self.date_joined.date()

    def toggle_status(self):
        self.is_active = not self.is_active
        self.save()





class Role(models.Model):
    name = models.CharField(
        verbose_name=_('Role Name'),
        max_length=150,
    )

    description = models.TextField(
        verbose_name=_('Description'),
        max_length=255,
        null=True, blank=True,
    )

    class Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
       

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @transaction.atomic()
    def delete(self, *args, **kwargs):
        group = self.get_group()
        group.delete()
        return super().delete(*args, **kwargs)

    def get_group(self):
       
        group_name = self.name

        return get_object_or_404(Group, name=group_name)

    def permissions(self):
        content_types = ContentType.objects.all().exclude(id__in=(1, 2, 3, 4, 5))
        content_types = content_types.order_by('pk').prefetch_related('permission_set')
        return content_types

    def assigned_permissions(self):
        group = self.get_group()
        current_permissions = group.permissions.all().order_by('content_type_id')
        return current_permissions

    def users(self):
        return self.profiles.all()

    @property
    def count_permissions(self):
        return self.permissions().count()

    @property
    def count_assigned_permissions(self):
        return self.assigned_permissions().count()

    @property
    def count_users(self):
        return 0  # self.users().count()

    @property
    def detail_url(self):
        return None






class Franchise(models.Model):
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='franchise/', blank=True, null=True)  
    email = models.EmailField(
        max_length=150,
        error_messages={'unique': _('A user with that email already exists.')},
        unique=False,
    )
    mobile = models.CharField(
        verbose_name=_('Contact Number'),
        max_length=32,
        validators=[],
    )
    alternate_mobile = models.CharField(
        verbose_name=_('Alternate Contact Number'),
        max_length=32,
        validators=[],
        null=True,
        blank=True
    )
    owner = models.CharField(max_length=200)
    short_name = models.CharField(max_length=200)
    gstid = models.CharField(max_length=15, unique=True,null=True,blank=True)
    city = models.CharField(max_length=50)
    
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    
    pincode = models.CharField(max_length=10, blank=True, null=True)
    no_of_students = models.IntegerField(default=0, blank=True, null=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    zone = models.CharField(max_length=200, blank=True, null=True)
    # New franchise_code field - allows null/blank for existing records
    franchise_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

   
    def __str__(self):
        return self.name
   
    