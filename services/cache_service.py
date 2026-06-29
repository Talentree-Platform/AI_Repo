import redis
import json
import logging

logger = logging.getLogger("talentree.services.cache")

class RedisManager:
    def __init__(self, host="127.0.0.1", port=6379, db=0):
        self.use_redis = True
        try:
            self.redis_client = redis.Redis(
                host=host, 
                port=port, 
                db=db, 
                socket_timeout=1.5, 
                socket_connect_timeout=1.5
            )
            # Ping to verify connection
            self.redis_client.ping()
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            self.use_redis = False
            logger.warning(f"Redis connection failed, falling back to in-memory dictionaries: {e}")
            # In-memory mock fallbacks
            self.chat_histories = {}
            self.exact_cache = {}
            self.semantic_cache = []

    def get_messages(self, session_id: str, max_count: int = 10) -> list[dict]:
        if self.use_redis:
            try:
                history_key = f"chat_history:{session_id}"
                raw_messages = self.redis_client.lrange(history_key, 0, max_count - 1)
                messages = []
                for m in reversed(raw_messages):
                    messages.append(json.loads(m.decode("utf-8")))
                return messages
            except Exception as e:
                logger.error(f"Redis get_messages error: {e}")
                return []
        else:
            return self.chat_histories.get(session_id, [])[-max_count:]

    def add_message(self, session_id: str, role: str, content: str):
        msg = {"role": role, "content": content}
        if self.use_redis:
            try:
                history_key = f"chat_history:{session_id}"
                self.redis_client.lpush(history_key, json.dumps(msg))
                # Keep history trimmed to 20 messages to prevent context length blowouts
                self.redis_client.ltrim(history_key, 0, 19)
            except Exception as e:
                logger.error(f"Redis add_message error: {e}")
        else:
            if session_id not in self.chat_histories:
                self.chat_histories[session_id] = []
            self.chat_histories[session_id].append(msg)
            if len(self.chat_histories[session_id]) > 20:
                self.chat_histories[session_id] = self.chat_histories[session_id][-20:]

    # Exact cache
    def set_cache(self, query: str, response: str, expire_seconds: int = 3600):
        key = query.strip().lower()
        if self.use_redis:
            try:
                cache_key = f"cache:exact:{key}"
                self.redis_client.setex(cache_key, expire_seconds, response)
            except Exception as e:
                logger.error(f"Redis set_cache error: {e}")
        else:
            self.exact_cache[key] = response

    def get_cache(self, query: str) -> str:
        key = query.strip().lower()
        if self.use_redis:
            try:
                cache_key = f"cache:exact:{key}"
                val = self.redis_client.get(cache_key)
                return val.decode("utf-8") if val else None
            except Exception as e:
                logger.error(f"Redis get_cache error: {e}")
                return None
        else:
            return self.exact_cache.get(key)

    # Semantic cache (Jaccard Similarity index check)
    def add_semantic_cache(self, query: str, response: str):
        if self.use_redis:
            try:
                # Add to a Redis List for semantic matching
                self.redis_client.rpush("cache:semantic:keys", query.strip().lower())
                self.redis_client.set(f"cache:semantic:val:{query.strip().lower()}", response)
            except Exception as e:
                logger.error(f"Redis add_semantic_cache error: {e}")
        else:
            self.semantic_cache.append((query.strip().lower(), response))

    def get_semantic_cache(self, query: str, threshold: float = 0.75) -> str:
        target = query.strip().lower()
        target_tokens = set(target.split())
        if not target_tokens:
            return None
            
        if self.use_redis:
            try:
                keys = self.redis_client.lrange("cache:semantic:keys", 0, -1)
                for k in keys:
                    k_str = k.decode("utf-8")
                    k_tokens = set(k_str.split())
                    if not k_tokens:
                        continue
                    intersection = target_tokens.intersection(k_tokens)
                    union = target_tokens.union(k_tokens)
                    jaccard = len(intersection) / len(union)
                    if jaccard >= threshold:
                        logger.info(f"Semantic Cache HIT! Jaccard similarity {jaccard:.2f} for query: '{k_str}'")
                        val = self.redis_client.get(f"cache:semantic:val:{k_str}")
                        if val:
                            return val.decode("utf-8")
            except Exception as e:
                logger.error(f"Redis get_semantic_cache error: {e}")
                return None
        else:
            for k_str, val in self.semantic_cache:
                k_tokens = set(k_str.split())
                if not k_tokens:
                    continue
                intersection = target_tokens.intersection(k_tokens)
                union = target_tokens.union(k_tokens)
                jaccard = len(intersection) / len(union)
                if jaccard >= threshold:
                    logger.info(f"Semantic Cache HIT! Jaccard similarity {jaccard:.2f} for query: '{k_str}'")
                    return val
        return None

# Global Redis manager service instance
redis_mgr = RedisManager()
