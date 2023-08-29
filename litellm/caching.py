import litellm
import time
def get_prompt(*args, **kwargs):
    # make this safe checks, it should not throw any exceptions
    if len(args) > 1:
        messages = args[1]
        prompt = " ".join(message["content"] for message in messages)
        return prompt
    if "messages" in kwargs:
        messages = kwargs["messages"]
        prompt = " ".join(message["content"] for message in messages)
        return prompt
    return None

class RedisCache():
    def __init__(self, host, port, password):
        import redis
        # if users don't provider one, use the default litellm cache
        self.redis_client = redis.Redis(host=host, port=port, password=password)

    def set_cache(self, key, value):
        self.redis_client.set(key, str(value))

    def get_cache(self, key):
        # TODO convert this to a ModelResponse object 
        return self.redis_client.get(key)

class InMemoryCache():
    def __init__(self):
        # if users don't provider one, use the default litellm cache
        self.cache_dict = {}

    def set_cache(self, key, value):
        #print("in set cache for inmem")
        self.cache_dict[key] = value
        #print(self.cache_dict)

    def get_cache(self, key):
        #print("in get cache for inmem")
        if key in self.cache_dict:
            #print("got a cache hit")
            return self.cache_dict[key]
        #print("got a cache miss")
        return None

class Cache():
    def __init__(self, type="local", host="", port="", password=""):
        if type == "redis":
            self.cache = RedisCache(type, host, port, password)
        if type == "local":
            self.cache = InMemoryCache()
        litellm.input_callback.append("cache")
        litellm.success_callback.append("cache")

    def get_cache_key(self, *args, **kwargs):
        prompt = get_prompt(*args, **kwargs)
        if prompt is not None:
            cache_key = prompt
            if "model" in kwargs:
                cache_key += kwargs["model"]
        elif "input" in kwargs:
            cache_key = " ".join(kwargs["input"])
            if "model" in kwargs:
                cache_key += kwargs["model"]
        else:
            return None
        return cache_key

    def generate_streaming_content(self, content):
        chunk_size = 5  # Adjust the chunk size as needed
        for i in range(0, len(content), chunk_size):
            yield {'choices': [{'delta': {'role': 'assistant', 'content': content[i:i+chunk_size]}}]}
            time.sleep(0.02)
    
    def get_cache(self, *args, **kwargs):
        try:  # never block execution
            cache_key = self.get_cache_key(*args, **kwargs)
            if cache_key is not None:
                cached_result = self.cache.get_cache(cache_key)
                if cached_result != None and 'stream' in kwargs and kwargs['stream'] == True:
                    # if streaming is true and we got a cache hit, return a generator
                    #print("cache hit and stream=True")
                    #print(cached_result)
                    return self.generate_streaming_content(cached_result["choices"][0]['message']['content'])
                return cached_result
        except:
            return None

    def add_cache(self, result, *args, **kwargs):
        try:
            # print("adding to cache", result)
            cache_key = self.get_cache_key(*args, **kwargs)
            # print(cache_key)
            if cache_key is not None:
                # print("adding to cache", cache_key, result)
                self.cache.set_cache(cache_key, result)
        except:
            pass





