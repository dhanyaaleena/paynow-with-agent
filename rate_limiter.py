import time
import asyncio
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    def __init__(self, tokens_per_second: int = 5):
        self.tokens_per_second = tokens_per_second
        # customer_id -> (tokens, last_refill_time)
        self.buckets: Dict[str, Tuple[float, float]] = {}
        self.lock = asyncio.Lock()

    async def is_allowed(self, customer_id: str) -> bool:
        """Check if request is allowed for the customer"""
        async with self.lock:
            current_time = time.time()

            # Get or create bucket for customer
            if customer_id not in self.buckets:
                # New customer starts with tokens_per_second tokens, but
                # consumes 1 immediately
                self.buckets[customer_id] = (
                    self.tokens_per_second - 1, current_time)
                return True

            tokens, last_refill = self.buckets[customer_id]

            # Calculate time since last refill
            time_passed = current_time - last_refill

            # Refill tokens based on time passed (only add whole tokens)
            tokens_to_add = int(time_passed * self.tokens_per_second)
            tokens = min(self.tokens_per_second, tokens + tokens_to_add)

            # Check if we have tokens available
            if tokens >= 1:
                tokens -= 1
                self.buckets[customer_id] = (tokens, current_time)
                return True
            else:
                # Update last refill time even if no tokens available
                self.buckets[customer_id] = (tokens, current_time)
                logger.warning(
                    f"Rate limit exceeded for customer {customer_id}")
                return False

    def get_bucket_status(self, customer_id: str) -> Tuple[float, float]:
        """Get current bucket status for debugging"""
        if customer_id not in self.buckets:
            return (self.tokens_per_second, time.time())

        tokens, last_refill = self.buckets[customer_id]
        current_time = time.time()

        # Calculate time since last refill
        time_passed = current_time - last_refill

        # Refill tokens based on time passed (only add whole tokens)
        tokens_to_add = int(time_passed * self.tokens_per_second)
        current_tokens = min(self.tokens_per_second, tokens + tokens_to_add)

        return (current_tokens, last_refill)


# Global rate limiter instance
rate_limiter = TokenBucketRateLimiter(tokens_per_second=5)
