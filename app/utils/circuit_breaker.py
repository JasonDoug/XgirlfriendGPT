import time
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    """
    Circuit Breaker pattern implementation to prevent cascade failures
    when external services (Ollama, ComfyUI, ElevenLabs, Cartesia) are failing or offline.
    """
    def __init__(self, name: str, failure_threshold: int = 3, recovery_time: float = 30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        
        self.state = "CLOSED" # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_failure_time = 0.0

    def __call__(self, func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            now = time.time()
            if self.state == "OPEN":
                if now - self.last_failure_time > self.recovery_time:
                    logger.info(f"Circuit Breaker '{self.name}' entering HALF_OPEN state.")
                    self.state = "HALF_OPEN"
                else:
                    raise CircuitBreakerOpenException(
                        f"Circuit Breaker '{self.name}' is OPEN. Target service is degraded."
                    )
            
            try:
                result = func(*args, **kwargs)
                if self.state == "HALF_OPEN":
                    logger.info(f"Circuit Breaker '{self.name}' recovered. Resetting to CLOSED.")
                    self.state = "CLOSED"
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = now
                if self.failure_count >= self.failure_threshold:
                    logger.error(f"Circuit Breaker '{self.name}' triggered OPEN due to {self.failure_count} consecutive failures: {e}")
                    self.state = "OPEN"
                raise e

        return wrapper
