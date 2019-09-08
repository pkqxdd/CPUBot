from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from .models import Record
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.conf import settings
from django.http import HttpRequest
from django.utils.timezone import now, timedelta
import requests
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail


from CPUBot.settings import BOT_TOKEN, CLIENT_ID, CLIENT_SECRET, API_ENDPOINT, GUILD_ID, REDIRECT_URI

@csrf_exempt
def join(request: HttpRequest):
    if request.method != 'POST':
        return HttpResponse("Invalid method", status=405)
    try:
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        school_email = request.POST['school_email']
        for s in (first_name, last_name, school_email):
            if not s:
                raise KeyError
    except KeyError as e:
        return HttpResponse("Missing field %s" %e, status=400)
    if not school_email.strip().endswith('@choate.edu'):
        return HttpResponse("Error: Please provide your Choate email", status=400)
    if Record.objects.filter(school_email=school_email).exists():
        return render(request,'confirmation_template.html',{"text":"You have already signed up for the club.",'Title':'Error'},status=400)
    try:
        record = Record(first_name=first_name,
                        last_name=last_name,
                        school_email=school_email)
        record.full_clean()
    except IntegrityError:
        return HttpResponse("DB Error", status=400)
    except ValidationError as e:
        res="Invalid input."
        for k,v in e.error_dict.items():
            res+='<br>{}: {}'.format(k,v)
        return HttpResponse(res, status=400)
    else:
        record.save(force_insert=True)
    
    
    auth_addr='{api}/oauth2/authorize?response_type=code&client_id={cid}&scope={scope}&state={state}&redirect_uri={redirect}'.format(
            api=API_ENDPOINT,
            cid=CLIENT_ID,
            scope='identify%20guilds.join',
            state=record.state,
            redirect=REDIRECT_URI
    )
    
    send_mail(
            subject='Welcome To Choate Programming Union',
            message=f"""
Hi {first_name},

Welcome to Choate Programming Union! To fully utilize the resources we provide, we strongly encourage you to join our Discord server.

Your invitation link is:
{auth_addr}
Please note that this link is private to you so please do not share it with others.

PS: If you happen to find this email in your spam folder, please log in to your Outlook account in your browser (desktop/mobile clients don't work).
Then navigate to your spam folder and report it as "not a spam". This will make sure you receive our future communications.

Your beloved,
CPU Bot
""",
            from_email='CPU Bot<bot@cpu.party>',
            recipient_list=[school_email],
            html_message=f"""
<!DOCType html>
<html>
<head>
    <title> Welcome To Choate Programming Union </title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        .monospace {{
            font-family: 'Courier New', monospace;
        }}
    </style>
</head>
    <body>
    <div class="monospace">
        <img src="https://cpu.party/img/logos/1024w.png" width="100%">
        <p>
            Hi {first_name},
        </p>
        <p>
            Welcome to Choate Programming Union! To fully utilize the resources we provide, we strongly encourage you to join our Discord server.
        </p>
        
<p>
        <a href="{auth_addr}">Click here</a> to join our server. Please note that this link is private to you so please do not share it with others.
</p>

<p>
PS: If you happen to find this email in your spam folder, please log in to your Outlook account in your browser (desktop/mobile clients don't work).
Then navigate to your spam folder and report it as "not a spam". This will make sure you receive our future communications.
</p>
<p>
Your beloved,<br>
CPU Bot
</p>
</div>
    </body>
</html>
"""
    )
    
    
    return render(request,'confirmation_template.html',{
        'title':'Success',
        'text':f"""
<h1> Success</h1>
<p>
Thank you, {first_name}. You have successfully signed up for the club. An email containing an invitation
link to our Discord server has been sent to <span style="text-decoration:underline">{school_email}</span>.
If you do not see it within 5 minutes, please check your spam folder. (If the email does end up in your
spam folder, please report it as not a spam email so you'll receive future emails from us.)
</p>
"""
    })
    


def callback(request: HttpRequest):
    try:
        code = request.GET['code']
        state = request.GET['state']
    except KeyError:
        error = request.GET.get('error', '')
        if error == 'access_denied':
            return HttpResponse("Access denied by user", status=403)
        return HttpResponse("Bad Request", status=400)
    
    try:
        record = Record.objects.get(state=state)
    except Record.DoesNotExist:
        return HttpResponse("Bad Request: state mismatch. Your request may be tempered.", status=400)
    
    if record.access_token is None:
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
            'scope': 'guilds.join%20identify'
        }
        
        r = requests.post('{api}/oauth2/token'.format(api=API_ENDPOINT), data, {
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        if r.status_code != 200:
            print(r, r.status_code, r.content)
            return HttpResponse("Bad OAuth, please try again", status=400)
        token_data = r.json()
        record.access_token = token_data['access_token']
        record.refresh_token = token_data['refresh_token']
        record.token_type = token_data['token_type']
        record.expires_at = now() + timedelta(seconds=int(token_data['expires_in']))
        record.save()
    
    headers = {'Authorization': '{type} {token}'.format(type=record.token_type, token=record.access_token)}
    r = requests.get('{api}/users/@me'.format(api=API_ENDPOINT), headers=headers)
    user_data = r.json()
    user_id = user_data['id']
    
    try:
        old=Record.objects.get(discord_user_id=user_id)
    except Record.DoesNotExist:
        pass
    else:
        old.delete()
    
    username = user_data['username']
    discriminator = user_data['discriminator']
    
    record.discord_username = '{}#{}'.format(username, discriminator)
    record.discord_user_id = user_id
    record.save()
    data = {
        'access_token': record.access_token,
        'nick': '{} {}'.format(record.first_name, record.last_name)
    }
    
    headers = {
        'Authorization': 'Bot {token}'.format(token=BOT_TOKEN),
    }
    
    r = requests.put("{api}/guilds/{guild_id}/members/{user_id}".format(
            api=API_ENDPOINT,
            guild_id=GUILD_ID,
            user_id=user_id
    ), json=data, headers=headers)
    
    if r.status_code != 201 and r.status_code != 204:
        print(r.status_code)
        print(r.content)
        return HttpResponse("Error joining server. Please try again.", status=400)
    
    record.join_success = True
    record.save()
    return HttpResponseRedirect('https://cpu.party/join/success')
    #return HttpResponse("Success. You may close this window/tab now.", status=200)
