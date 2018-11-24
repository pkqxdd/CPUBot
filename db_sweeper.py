from credentials import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
import sqlite3,requests,datetime

conn=sqlite3.connect('db.sqlite3')
cursor=conn.cursor()

swept_users=set()

API_ENDPOINT = 'https://discordapp.com/api/v6'

def refresh(refresh_token):
  data = {
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'grant_type': 'refresh_token',
    'refresh_token': refresh_token,
    'redirect_uri': REDIRECT_URI,
    'scope': 'identify guilds.join'
  }
  headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
  }
  r = requests.post('%s/oauth2/token' % API_ENDPOINT, data, headers)
  r.raise_for_status()
  return r.json()

def get_user_info(access_token):
    headers = {'Authorization': '{type} {token}'.format(type='Bearer', token=access_token)}
    r = requests.get('{api}/users/@me'.format(api=API_ENDPOINT), headers=headers)
    return r.json()
    

cursor.execute("SELECT first_name,last_name,school_email,refresh_token,join_success,opt_out_pm,opt_out_email,state,time_requested FROM oauth_record WHERE join_success=1 ORDER BY id DESC")
res=cursor.fetchall()
c=0
for first_name,last_name,school_email,refresh_token,join_success,opt_out_pm,opt_out_email,state,time_requested in res:
    if (first_name.strip() + ' ' + last_name.strip()).title() in swept_users:
        print('Removed (duplicate)',first_name, last_name,)
        continue
    
    if school_email.strip() in swept_users:
        print('Removed (duplicate)', school_email )
        continue
    
    new=refresh(refresh_token)
    
    token=new['access_token']
    info=get_user_info(token)
    
    user_id=info['id']
    if user_id in swept_users:
        print('Removed (duplicate)', user_id )
        continue
    
    cursor.execute('INSERT INTO oauth_record_copy (access_token,discord_user_id,discord_username,expires_at,first_name,id,join_success,last_name,opt_out_email,opt_out_pm,refresh_token,school_email,state,time_requested,token_type) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (token,user_id,info['username']+'#'+str(info['discriminator']),datetime.datetime.now()+datetime.timedelta(seconds=new['expires_in']),first_name.title().strip(),c,1,last_name.title().strip(),opt_out_email,opt_out_pm,refresh_token,school_email.strip(),state,time_requested,new['token_type']))
    swept_users.add((first_name.strip() + ' ' + last_name.strip()).title())
    swept_users.add(school_email.strip())
    swept_users.add(user_id)
    print('Added',first_name,last_name)
    c+=1

    

cursor.execute("SELECT first_name,last_name,school_email,refresh_token,join_success,opt_out_pm,opt_out_email,state,time_requested FROM oauth_record WHERE join_success=0 ORDER BY id DESC")
res=cursor.fetchall()
for first_name,last_name,school_email,refresh_token,join_success,opt_out_pm,opt_out_email,state,time_requested in res:
    if (first_name.strip()+' '+last_name.strip()).title() in swept_users:
        print('Removed (duplicate)', first_name, last_name, )
        continue
        
    if school_email.strip() in swept_users:
        print('Removed (duplicate)', school_email)
        continue
    
    cursor.execute('INSERT INTO oauth_record_copy (access_token,discord_user_id,discord_username,expires_at,first_name,id,join_success,last_name,opt_out_email,opt_out_pm,refresh_token,school_email,state,time_requested,token_type) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (None,None,None,None,first_name.title().strip(),c,0,last_name.title().strip(),0,0,None,school_email.strip(),state,time_requested,None))
    
    swept_users.add((first_name.strip() + ' ' + last_name.strip()).title())
    swept_users.add(school_email.strip())
    c+=1
conn.commit()


