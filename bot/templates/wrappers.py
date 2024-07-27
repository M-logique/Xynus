from functools import wraps
from ..utils.functions import disable_all_items

def check_views(coro):
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        

        ctx = args[1]
        client = args[0].client
        user_id = ctx.author.id

        prev_view = client.view_cache.get(user_id)

        if prev_view:
            await disable_all_items(prev_view)
            del client.view_cache[user_id]

        
        return await coro(*args, **kwargs)
        
    
    return wrapper