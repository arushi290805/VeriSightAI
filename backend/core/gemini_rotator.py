import itertools

from google import genai
from google.api_core.exceptions import ResourceExhausted

from core.config import get_gemini_api_keys


class GeminiKeyRotator:
    def __init__(self):
        self.keys = get_gemini_api_keys()

        if not self.keys:
            print(
                "WARNING: No Gemini API keys provided in "
                "GEMINI_API_KEYS environment variable."
            )
            self.key_cycle = itertools.cycle(["dummy_key"])
        else:
            self.key_cycle = itertools.cycle(self.keys)

    def get_next_key(self):
        return next(self.key_cycle)

    def execute_with_retry(self, func, *args, **kwargs):
        if not self.keys:
            # For testing without real keys, or fail gracefully
            raise ValueError("No Gemini API keys available for execution.")

        attempts = 0
        max_attempts = len(self.keys) * 2  # Try each key up to 2 times

        while attempts < max_attempts:
            key = self.get_next_key()

            # New google-genai SDK
            client = genai.Client(api_key=key)

            try:
                return func(client, *args, **kwargs)

            except ResourceExhausted as e:
                attempts += 1
                if attempts >= max_attempts:
                    raise e

            except Exception as e:
                msg = str(e).lower()
                retryable = any(
                    token in msg
                    for token in ("429", "resource exhausted", "quota", "rate limit", "unavailable", "overloaded")
                )
                if retryable:
                    attempts += 1
                    if attempts >= max_attempts:
                        raise e
                    continue
                raise e


rotator = GeminiKeyRotator()