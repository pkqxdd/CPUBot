import discord,collections

def split_message(msg, enclose_in='', separator='\n', limit=2000):
    limit = limit - len(enclose_in) * 2
    assert limit > 0
    
    res = []
    remainder = msg
    while len(remainder) >= limit:
        new = remainder[:limit]
        index = new.rfind(separator)
        
        if index > 0:
            remainder = remainder[index + len(separator):]
            new = new[:index + len(separator)]
        else:
            remainder = remainder[limit:]
        
        res.append(enclose_in + new + enclose_in)
    res.append(enclose_in + remainder + enclose_in)
    return res


async def send_messages(to, msgs,**kwargs):
    assert isinstance(to, discord.abc.Messageable)
    assert isinstance(msgs, collections.Iterable)
    
    res = []
    for msg in msgs:
        res.append(await to.send(msg,**kwargs))
    return res


async def split_send_message(to, msg, enclose_in='', separator='\n',**kwargs):
    assert isinstance(to, discord.abc.Messageable)
    assert isinstance(msg, str)
    msgs = split_message(msg, enclose_in, separator)
    return await send_messages(to, msgs,**kwargs)
