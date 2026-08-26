import time
import hashlib
import json
from functools import wraps
from datetime import datetime
from sqlalchemy.orm import Session
from models.schema import TelemetryLogDB
from core.config import settings

_response_cache = {}

def with_telemetry(step_name: str):
    """
    Decorator that caches identical Gemini calls in-memory 
    and logs telemetry to SQLite if an actual call is made.
    Requires `db: Session` to be passed to the wrapped function as a kwarg.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            db: Session = kwargs.get("db")
            
            # Create cache key from all args/kwargs (excluding db)
            cache_kwargs = {k: v for k, v in kwargs.items() if k != "db"}
            
            # Simple hash logic for prototype (assumes args are serializable strings/dicts)
            hash_input = json.dumps({"args": args, "kwargs": cache_kwargs}, default=str, sort_keys=True)
            cache_key = hashlib.md5(hash_input.encode()).hexdigest()
            
            if cache_key in _response_cache:
                return _response_cache[cache_key]
                
            start_time = time.time()
            
            # Execute actual call
            response_text = func(*args, **kwargs)
            
            latency_ms = (time.time() - start_time) * 1000.0
            
            # In google-generativeai, we would normally parse `response.usage_metadata.prompt_token_count`
            # Since the wrapped function might just return the text, we approximate or extract it.
            # To do this right, the wrapped function should return the raw `response` object so we can read tokens.
            # For this prototype decorator, if func returns string, we approximate. 
            # If it returns the object, we extract.
            
            tokens_in = len(hash_input) // 4 # rough approximation if raw object is not returned
            tokens_out = len(response_text) // 4
            
            if hasattr(response_text, "usage_metadata"):
                tokens_in = response_text.usage_metadata.prompt_token_count
                tokens_out = response_text.usage_metadata.candidates_token_count
                text = response_text.text
            else:
                text = response_text
                
            cost = ((tokens_in + tokens_out) / 1000.0) * settings.GEMINI_PRICE_PER_1K_TOKENS
            
            _response_cache[cache_key] = text
            
            if db:
                log = TelemetryLogDB(
                    timestamp=datetime.now(),
                    step=step_name,
                    model=settings.GEMINI_MODEL,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=latency_ms,
                    estimated_cost_usd=cost
                )
                db.add(log)
                db.commit()
                
            return text
        return wrapper
    return decorator
