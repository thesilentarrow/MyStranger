from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db.models.signals import post_save
from django.dispatch import receiver
from friend.models import FriendList
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings



# Create your models here.


class MyAccountManager(BaseUserManager):
    def create_user(self, email, name,university_name, password=None):
        if not email:
            raise ValueError('Users must have an email address')
        else:
            college_email = email.split('.')[-1:]
            if not (college_email == ['edu']):
                college_email = email.split('.')[-2:]
                if not (college_email == ['edu', 'in'] or college_email == ['ac', 'in']):
                    raise ValueError(f'Email must ends with either .edu or .edu.in or .ac.in')
        if not university_name:
            raise ValueError('Users must have a University')

            # college_email = email.split('.')[-2:]
            # if not (college_email == ['edu', 'in']):
            #     raise ValueError('Email must ends with .edu.in')

        user = self.model(
            email=self.normalize_email(email),
            name=name,
            university_name=university_name,
            
        )

        user.set_password(password)
        user.save(using=self._db)
        return user
    

    def create_superuser(self, email, name,university_name, password):
        user = self.create_user(
            email=self.normalize_email(email),
            password=password,
            name=name,
            university_name=university_name,
           
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class Account(AbstractBaseUser):
    email = models.EmailField(verbose_name="email",
                              max_length=100, unique=True, null=False)
    name = models.CharField(max_length=100, default='Stranger')
    university_name = models.CharField(max_length=100, default='Unknown',blank=False)
    bio = models.CharField(max_length=5000,blank=True, null=True, default='')
    # universityName = models.CharField(max_length=200, default="",blank=True)
    origin = models.BooleanField(default=False)
    flags = models.IntegerField(default=0, blank=True)
    date_joined = models.DateTimeField(
        verbose_name='date joined', auto_now_add=True)
    last_login = models.DateTimeField(verbose_name='last login', auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    terms = models.BooleanField(default=True,blank=False,null=False)
    notif = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    last_activity = models.DateTimeField(verbose_name='last activity', default=timezone.now)

    confesser_id = models.CharField(max_length=100, default='None', null=True)
    ntoken = models.CharField(max_length=1000, default='None', null=True, blank=True)

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    gender = models.CharField(
        max_length=1,
        null=False,
        choices=GENDER_CHOICES,
        default='M',  # Set a default value
        verbose_name=_('Gender')
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name','university_name']

    objects = MyAccountManager()

    def __str__(self):
        return self.email

    # For checking permissions. to keep it simple all admin have ALL permissons
    def has_perm(self, perm, obj=None):
        return self.is_admin

    # Does this user have permission to view this app? (ALWAYS YES FOR SIMPLICITY)
    def has_module_perms(self, app_label):
        return True
    
    def update_last_activity(self):
        self.last_activity = timezone.now()
        self.save()

@receiver(post_save, sender=Account)
def _post_save_receiver(sender, instance, **kwargs):
	chat = FriendList.objects.get_or_create(user=instance)


class AccountToken(models.Model):
    user = models.OneToOneField(Account , on_delete=models.CASCADE)
    auth_token = models.CharField(max_length=100 )
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.email

class RegistrationError(models.Model):

    email = models.CharField(max_length=100 )
    uni_name = models.CharField(max_length=100 )
    uni_address = models.CharField(max_length=400 )
    issue_faced = models.CharField(max_length=10000 )
    is_resolved = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return str(self.email)

class deleted_account(models.Model):

    email = models.CharField(max_length=150, blank=False)
    name = models.CharField(max_length=100)
    reason = models.CharField(max_length=10000)
    is_resolved = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.email)
    
class Prompt(models.Model):
    user =              models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prompts')
    question			= models.CharField(max_length=1000, unique=False, blank=False,)
    answer			= models.CharField(max_length=5005, unique=False, blank=False,)
    timestamp           = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.name


