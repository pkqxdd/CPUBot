import asyncio.subprocess
import datetime
import functools
import logging
import secrets
import sqlite3
import textwrap
import time
import traceback
import types

import collections
import discord
import discord.abc

from credentials import BOT_TOKEN
from utils import split_message, send_messages, split_send_message

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)

handler = logging.FileHandler(filename='/var/tmp/CPUBot.log', encoding='utf-8', mode='a+')
handler.setLevel(logging.WARNING)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

handler = logging.FileHandler(filename='/var/tmp/CPUBot.verbose.log', encoding='utf-8', mode='a+')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

bot = discord.Client()

allowed_guild_ids = (479544231875182592, 426702004606337034)
CPU_guild_id = 426702004606337034

conn = sqlite3.Connection('db.sqlite3')
cursor = conn.cursor()

attendance_key = secrets.token_hex(32)
effective_meeting_count=1


class InterfaceMeta(type):
    
    def __init__(cls, *args, **kwargs):
        cls._interfaces = {}
        super().__init__(*args, **kwargs)
    
    def __call__(cls, channel: discord.abc.PrivateChannel, *args, **kwargs):
        if channel.id in cls._interfaces:
            return cls._interfaces[channel.id]
        obj = cls.__new__(cls, *args, **kwargs)
        obj.__init__(channel, *args, **kwargs)
        cls._interfaces[channel.id] = obj
        return obj


class BaseInterface(metaclass=InterfaceMeta):
    """
    Each method in subclass of BaseInterface must return a tuple
    The output of split_message is recommended.
    Every interface function must have signature
    (self,command: list, message: discord.Message)
    """
    error_reply = "Error"
    
    def __init__(self, channel: discord.abc.PrivateChannel):
        self._dispatch_locked = False
        self._channel = channel
    
    def unrecognized_command(self, command) -> str:
        return ("Unrecognized command `%s`." % command) + self.usage
    
    async def dispatch(self, command: str, message) -> list:
        if not self._dispatch_locked:
            if command == attendance_key:
                cursor.execute('INSERT INTO attendance VALUES (?,?,?)', (
                '%s#%s' % (message.author.name, message.author.discriminator), datetime.datetime.now(), effective_meeting_count))
                conn.commit()
                return await split_send_message(message.author, 'Thank you. Your attendance has been recorded.')
            try:
                command = command.split()
                func = getattr(self, command[0])
                reply= await func(command[1:] if len(command) > 1 else [],message)
                if isinstance(reply,str):
                    reply=(reply,)
                return await send_messages(message.author,reply)
            except AttributeError:
                return await split_send_message(message.author, self.error_reply)
            except IndexError:
                return await split_send_message(message.author, 'Insufficient arguments.\n' + self.usage)
        else:
            return []
    
    def lock_dispatch(self):
        self._dispatch_locked = True
    
    def unlock_dispatch(self):
        self._dispatch_locked = False
    
    @property
    def usage(self) -> str:
        res = 'Usage:\n'
        for cls in self.__class__.__mro__:
            for name, attr in cls.__dict__.items():
                if isinstance(attr, types.FunctionType) and hasattr(attr, 'usage'):
                    res += '```' + attr.usage + '```'
                    if hasattr(attr, 'description'):
                        res += attr.description
                    res += '\n\n'
        return res


class Conversation:
    def __init__(self, interface: BaseInterface):
        self.interface = interface
    
    def __enter__(self):
        self.interface.lock_dispatch()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.interface.unlock_dispatch()
    
    async def send(self, msg, enclose_in, separator):
        await split_send_message(self.interface._channel,msg,enclose_in,separator)
    
    async def recv(self,timeout=1800) -> discord.Message:
        return await bot.wait_for('message', check=lambda msg:msg.channel==self.interface._channel and not msg.author.bot, timeout=timeout)



class UserInterface(BaseInterface):
    @property
    def error_reply(self):
        return textwrap.dedent("""
                Sorry I'm not evolved enough to answer your question or even reply properly.
                use the `#general` channel of CPU server for general discussions about programming as well as the club;
                use the `#help` channel if you need any help with your programming project or homework;
                the club leaders and are ready to help––specifically, the leaders are proficient in:
                \t- Python (CPython)
                \t- Java
                \t- C++
                \t- HTML (Hypertext Markup Language)
                \t- CSS (Cascade Style Sheets)
                \t- JS (JavaScript, also known as ECMAScript)
                \t- Bash (Bourne again shell);
                use the `#lounge` channel for memes, jokes, chats, flirting, and everything else.
                Please redirect any question about me to my creator Jerry `pkqxdd#1358`.
                
                I also support some basic commands. """) + self.usage
    
    @staticmethod
    def next_message(channel):
        def check(msg):
            return msg.channel == channel and not msg.author.bot
        
        return check
    
    async def feedback(self, command: list, message: discord.Message) -> tuple:
        
        with Conversation(self) as con:
            feedback_channel = discord.utils.find(lambda c: c.name == 'feedback', CPU_guild.channels)
            await con.send('Your next message to me will be forwarded to the admin team anonymously. Type `cancel` to cancel.')
            try:
                msg_to_forward=await con.recv()
            except asyncio.TimeoutError:
                return 'You have not responded in 30 minutes. I will no longer forward your next message to the admin team.',
            if msg_to_forward.content == 'cancel':
                return 'Operation canceled.',
            try:
                await feedback_channel.send(msg_to_forward.content)
            except:
                await on_error('feedback')
                return 'Sorry an error has occurred.',
            return 'Your feedback has been forwarded to the admin team. Thank you.',
        
        # try:
        #     self.lock_dispatch()
        #     feedback_channel = discord.utils.find(lambda c: c.name == 'feedback', CPU_guild.channels)
        #     await self._channel.send(
        #         'Your next message to me will be forwarded to the admin team anonymously. Type `cancel` to cancel.')
        #
        #     try:
        #         msg_to_forward = await bot.wait_for('message', check=self.next_message(message.channel), timeout=1800)
        #     except asyncio.TimeoutError:
        #         return 'You have not responded in 30 minutes. I will no longer forward your next message to the admin team',
        #
        #     if msg_to_forward.content == 'cancel':
        #         return 'Operation canceled',
        #
        #     try:
        #         await feedback_channel.send(msg_to_forward.content)
        #     except:
        #         await on_error('feedback')
        #         return 'Sorry an error has occurred',
        #
        #     return 'Your feedback has been forwarded to the admin team. Thank you.',
        # finally:
        #     self.unlock_dispatch()
    
    feedback.usage = 'feedback'
    feedback.description = 'Send a feedback to the admin team anonymously.'
    
    async def opt(self, command: list, message: discord.Message) -> tuple:
        try:
            discord_username = '{}#{}'.format(message.author.name, message.author.discriminator)
            if command[0] == 'out':
                if command[1] == 'email':
                    cursor.execute("UPDATE oauth_record SET opt_out_email=1 WHERE discord_username=?",
                                   (discord_username,))
                    conn.commit()
                    return "You have successfully opted out of our email",
                elif command[1] == 'dm':
                    cursor.execute("UPDATE oauth_record SET opt_out_pm=1 WHERE discord_username=?", (discord_username,))
                    conn.commit()
                    return "You have successfully opted out of our private message",
                else:
                    return self.unrecognized_command(command[1]),
            elif command[1] == 'in':
                if command[1] == 'email':
                    cursor.execute("UPDATE oauth_record SET opt_out_email=0 WHERE discord_username=?",
                                   (discord_username,))
                    conn.commit()
                    return "You have successfully opted in our email",
                elif command[1] == 'dm':
                    cursor.execute("UPDATE oauth_record SET opt_out_pm=0 WHERE discord_username=?", (discord_username,))
                    conn.commit()
                    return "You have successfully opted in our direct message",
                else:
                    return self.unrecognized_command(command[1]),
            else:
                return self.unrecognized_command(command[0]),
        except IndexError:
            raise
        except:
            await on_error('preference change')
            return 'An error has occurred',
    
    opt.usage = 'opt (in|out) (email|dm)'
    opt.description = 'Change your preference of whether you want to receive notification by a specific method for announcements.'
    
    async def attendance(self, command, message) -> tuple:
        username = f'{message.author.name}#{message.author.discriminator}'
        if command[0]=='status':
            cursor.execute('SELECT sum(effective), count() FROM attendance where discord_username=?',(username,))
            res=cursor.fetchone() # only one row will be returned
            if res[1]==0:
                return 'You have not attended any meeting this year.',
            if res[0]==res[1]:
                return f"You have attended {res[1]} meeting{'s' if res[1]>1 else ''} this year.",
            return f"You have attended {res[1]} meeting{'s' if res[1]>1 else ''} this year, which count{'s' if res[1]==1 else ''} as {res[0]} meetings with bonuses.",
        
        elif command[0]=='list':
            cursor.execute('SELECT time, effective FROM attendance where discord_username=?', (username,))
            res=cursor.fetchall()
            reply='You have attended the following meetings:\n'
            for att in res:
                reply+=att[0].split()[0]
                if att[1]!=1:
                    reply+=f' (counts as {att[1]} meetings)'
                reply+='\n'
            return split_message(reply)
        else:
            return self.unrecognized_command(command[0]),
    
    attendance.usage='attendance (status|list)'
    attendance.description='Show the number of meetings you have attended'
        


class AdminInterface(UserInterface):
    @property
    def error_reply(self):
        return self.usage
    
    @staticmethod
    async def run_shell(command: list, channel):
        timeout = 15
        if command[0] in ('aria2c', 'curl', 'wget', 'git', 'http'):
            timeout = 120
        
        def kill(proc):
            if proc.returncode is None:
                proc.kill()
                proc.killed_by_bot = True
        
        command = ' '.join(command)
        await channel.send("Executing shell command `%s`" % command)
        async with channel.typing():
            PIPE = asyncio.subprocess.PIPE
            DEVNULL = asyncio.subprocess.DEVNULL
            proc = await asyncio.subprocess.create_subprocess_shell(command, stdin=DEVNULL, stderr=PIPE, stdout=PIPE)
            proc.killed_by_bot = False
            bot.loop.call_later(timeout, kill, proc)
            buffer = ''
            timer = time.time()
            while proc.returncode is None:
                if not proc.stdout.at_eof():
                    buffer += (await proc.stdout.readline()).decode()
                if not proc.stderr.at_eof():
                    buffer += (await proc.stderr.readline()).decode()
                
                if time.time() - timer > 1 or len(buffer) > 1500:
                    asyncio.ensure_future(split_send_message(channel, buffer, '```'))
                    buffer = ''
                    timer = time.time()
                    await asyncio.sleep(0.1)
            buffer += (await proc.stdout.read()).decode()
            buffer += (await proc.stderr.read()).decode()
            if buffer:
                await split_send_message(channel, buffer, '```')
            if proc.killed_by_bot:
                await channel.send(
                        "Operation exceeded the %d seconds timeout, so I had to kill it:sweat_smile:" % timeout)
            await channel.send("Process terminated with exit code %d" % proc.returncode)
    
    async def sql(self, command: list, message: discord.Message) -> list:
        command = list(map(lambda s: s.lower(), command))
        try:
            if 'select' not in command or any(kw in command for kw in (
                    'update', 'insert', 'drop', 'alter', 'table', 'into', 'create', 'value')):
                reply = "Only SELECT statement is allowed. Please, don't try to break the server...because you will."
            else:
                cursor.execute(' '.join(command))
                reply = str(' '.join(col[0] for col in cursor.description) + '\n' + '\n'.join(
                        map(str, (cursor.fetchall()))))
        except:
            reply = str(traceback.format_exc())
        
        return split_message(reply, enclose_in='```')
    
    sql.usage = 'sql $sql_select_query'
    sql.description = 'Query the database. Currently existing tables are `oauth_record` and `attendance`.'
    
    async def email(self, command: list, message: discord.Message) -> list:
        if command[0] == 'list':
            cursor.execute('SELECT DISTINCT school_email FROM oauth_record')
            reply = ''
            for res in cursor.fetchall():
                reply += res[0] + '\n'
        else:
            reply = self.unrecognized_command(command[0])
        
        return split_message(reply)
    
    email.usage = 'email list'
    email.description = 'List all unique emails in the database.'
    
    async def shell(self, command: list, message: discord.Message) -> tuple:
        if message.author in superusers:
            await self.run_shell(command, message.channel)
            return ()
        else:
            return ('Permission denied',)
    
    shell.usage = 'shell $*'
    shell.description = 'Run shell command `$*` in `/srv/CPUBot/` with root privilege.'
    
    async def meeting(self, command: list, message: discord.Message) -> list:
        global attendance_key,effective_meeting_count
        if command[0] == 'begin':
            attendance_key = secrets.token_hex(3)
            try:
                effective_meeting_count=int(command[1])
            except (IndexError,ValueError):
                pass
                
            reply = 'Attendance key: `%s`' % attendance_key
        elif command[0] == 'end':
            attendance_key = secrets.token_hex(64)
            effective_meeting_count=1
            reply = 'Meeting is over. Attendance key revoked.'
        else:
            reply = self.unrecognized_command(command[0])
        return split_message(reply)
    
    meeting.usage = 'meeting [begin|end]'
    meeting.description = 'Starts or ends a club meeting. Change the status of attendance system accordingly.'
    
    async def restart(self, command: list, message: discord.Message):
        if message.author in superusers:
            await self.run_shell(['service', 'CPUBot', 'restart'], message.channel)
            return ()
        else:
            return ('Permission denied',)
    
    restart.usage = 'restart'
    restart.description = 'Restart CPUBot'

    async def attendance(self, command, message):
        if command[0]=='today':
            cursor.execute("SELECT first_name, last_name FROM attendance a "
                           "JOIN (SELECT first_name, last_name, discord_username FROM oauth_record GROUP BY school_email) o "
                           "ON o.discord_username=a.discord_username WHERE a.time>? AND a.time<?; ",(datetime.date.today()-datetime.timedelta(1),datetime.date.today()+datetime.timedelta(1)))
            res=cursor.fetchall()
            if not res:
                return "Nobody has attended today's meeting",
            reply=''
            for p in res:
                reply+=p[0]+' '+p[1]+'\n'
            return split_message(reply)
        else:
            return await super().attendance(command,message)
        
    attendance.usage='attendance today'
    attendance.description='Show people who have attended the meeting today'
    
@bot.event
async def on_ready():
    print('Logged in as %s' % bot.user.name)
    game = discord.Game("with the source code of life")
    await bot.change_presence(activity=game)
    global author, superusers, admins, CPU_guild
    author = bot.get_user(268759214610972673)
    superusers = [
        bot.get_user(387486747770224642),
    ]
    
    superusers.append(author)
    
    admins = [
                 bot.get_user(427179609084264449),
                 bot.get_user(119211672513675265),
                 bot.get_user(386377340743057408)
             ] + superusers
    
    CPU_guild = discord.utils.find(lambda g: g.id == CPU_guild_id, bot.guilds)


@bot.event
async def on_member_join(member):
    await member.send('''
Welcome to CPU. Please adhere to the rules pinned in `#announcements` channel. 
use the `#general` channel of CPU server for general discussions about programming as well as the club;
use the `#help` channel if you need any help with your programming project or homework;
the club leaders and are ready to help––specifically, the leaders are proficient in: 
\t- Python (CPython)
\t- Java
\t- C++ 
\t- HTML (Hypertext Markup Language)
\t- CSS (Cascade Style Sheets)
\t- JS (JavaScript, also known as ECMAScript)
\t- Bash (Bourne again shell);
use the `#lounge` channel for memes, jokes, chats, flirting, and everything else.
Please redirect any question about me to my creator Jerry `pkqxdd#1358`.
So good luck, have fun coding!'''.strip())
    channel = discord.utils.get(member.guild.channels, name='new-members-welcome')
    try:
        await channel.send(f"{member.nick} has joined the party. Welcome!")
    except AttributeError:
        pass  # Channel does not exist


@bot.event
async def on_message(message):
    if not message.author.bot:
        if isinstance(message.channel, discord.DMChannel):
            if message.author in admins:
                interface = AdminInterface(message.channel)
            else:
                interface = UserInterface(message.channel)
            try:
                await interface.dispatch(message.content, message)
            except:
                try:
                    await message.author.send("An error has occurred. My creator has been notified (well, hopefully).")
                except:
                    pass
                raise
        elif message.channel.name.lower() == 'announcements':
            make_announcement(message)


def make_announcement(message):
    tasks = []
    confirm = False
    if message.mention_everyone:
        tasks.append(message.channel.delete_messages((message,)))
        tasks.append(message.author.send(
                "I have deleted your announcement because you mentioned everyone. Remember, I will add appropriate greetings to each announcement."))
        tasks.append(message.author.send(
                embed=discord.Embed(title="Your original announcement", description=message.content)))
    elif any(kw in message.content[:15].lower() for kw in
             ('hi', 'hello', 'sup', "what's up", "dear all", 'all', 'yall')):
        tasks.append(message.channel.delete_messages((message,)))
        tasks.append(message.author.send(
                "I have deleted your announcement because you added a greeting word at the beginning of the announcement. Remember, I will add appropriate greetings to each announcement."))
        tasks.append(message.author.send(
                embed=discord.Embed(title="Your original announcement", description=message.content)))
    
    else:
        message_body = message.clean_content
        recipients = []
        confirm = True
        for member in message.channel.members:
            if not member.bot:
                
                username = '%s#%s' % (member.name, member.discriminator)
                try:
                    message_header = f"Hi {bot.users_cache[username][0]}"
                except KeyError:
                    cursor.execute(
                            'SELECT DISTINCT first_name,last_name,discord_username, id FROM oauth_record WHERE discord_username=? ORDER BY id DESC LIMIT 1',
                            (username,))
                    record = cursor.fetchone()
                    if record is None:
                        message_header = f"Hi {member.name}"
                    else:
                        bot.users_cache[record[2]] = record[:2]
                        message_header = f"Hi {record[0]}"
                if member != message.author and member in superusers:
                    message_header += f', here is an announcement from CPU by {message.author.nick}:\n'
                else:
                    message_header += ','
                recipients.append(member)
                tasks.append(member.send(message_header + '\n' + message_body))
        
        tasks.append(message.channel.delete_messages((message,)))
        tasks.append(message.channel.send('Hi everyone,\n' + message.content))
    
    future = asyncio.gather(*tasks, return_exceptions=True)
    if confirm:
        callback = functools.partial(announcement_succeeded, recipients=recipients, confirm_to=message.author,
                                     time_started=time.time(), embed=discord.Embed(title='Your announcement',
                                                                                   description='Hi $name,\n' + message_body))
        future.add_done_callback(callback)
    asyncio.ensure_future(future)


def announcement_succeeded(future, recipients, confirm_to, time_started, embed):
    time_spent = round(time.time() - time_started, 2)
    results = future.result()
    failed_list = []
    try:
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                failed_list.append(recipients[i])
    except IndexError:
        pass
    if len(results) - 2 != len(recipients):
        print(len(results))
        print(len(recipients))
        return  # We have a problem
    sch = []
    if not failed_list:
        msg = f"Your announcement has been successfully sent to all {len(recipients)} members in {time_spent} seconds"
        embed.title = msg
        sch.append(confirm_to.send(embed=embed))
    else:
        msg = f"Your announcement has been successfully sent to {len(recipients)-len(failed_list)}/{len(recipients)} members in {time_spent} seconds"
        embed.title = msg
        sch.append(confirm_to.send(embed=embed))
        sch.append(confirm_to.send('Failed for:\n' + '\n'.join(m.nick or m.name for m in recipients)))
    
    asyncio.ensure_future(asyncio.gather(*sch))


@bot.event
async def on_error(event_method, *args, **kwargs):
    try:
        stacktrace = traceback.format_exc()
        msg = 'Error at `{time}` during handling event `{event}`. Stacktrace: \n```{trace}```\n'.format(
                time=datetime.datetime.now().isoformat(),
                event=event_method,
                trace=stacktrace
        )
        if args:
            msg += 'Args:\n'
            for arg in args:
                msg += '```{}```\n'.format(arg)
        if kwargs:
            msg += 'Kwargs:\n'
            for key, value in kwargs.items():
                msg += '```{k}: {v}```\n'.format(k=key, v=value)
        await split_send_message(author, msg)
    except:
        pass
    finally:
        await discord.Client.on_error(bot, event_method, *args, **kwargs)


cursor.execute('SELECT first_name, last_name, discord_username FROM oauth_record WHERE join_success = 1')
bot.users_cache = {}

for record in cursor.fetchall():
    bot.users_cache[record[2]] = record[:2]

if __name__ == '__main__':
    bot.run(BOT_TOKEN)
