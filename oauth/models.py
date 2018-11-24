from django.db import models
import secrets

class Record(models.Model):
    time_requested=models.DateTimeField("Time Requested",auto_now_add=True)
    first_name=models.CharField("First Name",max_length=100)
    last_name=models.CharField("Last Name",max_length=100)
    discord_username=models.CharField("Discord Username",max_length=100,blank=True,null=True)
    discord_user_id=models.IntegerField("Discord User ID",blank=True,null=True,unique=True)
    school_email=models.EmailField("School Email")
    state=models.CharField("Token", blank=True, max_length=32, unique=True)
    access_token=models.CharField("Access Token",blank=True,null=True,max_length=255)
    refresh_token=models.CharField("Refresh Token",blank=True,null=True,max_length=255)
    token_type=models.CharField("Token type",max_length=20,blank=True,null=True)
    expires_at=models.DateTimeField("Expires at",null=True,blank=True)
    join_success=models.BooleanField("Successfully joined the server",default=False)
    opt_out_email=models.BooleanField("Opted out email",default=False)
    opt_out_pm=models.BooleanField("Opted out discord private message",default=False)
    
    def save(self,*args,**kwargs):
        if not self.pk:  # on creation
            while True:
                token = secrets.token_hex(16)
                try:
                    Record.objects.get(state=token)
                except Record.DoesNotExist:
                    break
            self.state = token
    
        super().save(*args, **kwargs)
