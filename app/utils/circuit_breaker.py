import time
import logging
import threading
import inspect
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
        self._probing = False
        self._lock = threading.Lock()

    def __call__(self, func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                now = time.monotonic()
                with self._lock:
                    if self.state == "OPEN":
                        if now - self.last_failure_time > self.recovery_time:
                            logger.info(f"Circuit Breaker '{self.name}' entering HALF_OPEN state.")
                            self.state = "HALF_OPEN"
                            self._probing = True
                        else:
                            raise CircuitBreakerOpenException(
                                f"Circuit Breaker '{self.name}' is OPEN. Target service is degraded."
                            )
                    elif self.state == "HALF_OPEN":
                        if self._probing:
                            raise CircuitBreakerOpenException(
                                f"Circuit Breaker '{self.name}' is HALF_OPEN and currently probing."
                            )
                        else:
                            self._probing = True

                try:
                    result = await func(*args, **kwargs)
                    with self._lock:
                        if self.state == "HALF_OPEN":
                            logger.info(f"Circuit Breaker '{self.name}' recovered. Resetting to CLOSED.")
                            self.state = "CLOSED"
                        self.failure_count = 0
                        self._probing = False
                    return result
                except Exception as e:
                    now_end = time.monotonic()
                    with self._lock:
                        self.failure_count += 1
                        self.last_failure_time = now_end
                        self._probing = False
                        if self.failure_count >= self.failure_threshold:
                            logger.error(f"Circuit Breaker '{self.name}' triggered OPEN due to {self.failure_count} consecutive failures: {e}")
                            self.state = "OPEN"
                    raise e

            return async_wrapper

        def wrapper(*args, **kwargs):
            now = time.monotonic()
            with self._lock:
                if self.state == "OPEN":
                    if now - self.last_failure_time > self.recovery_time:
                        logger.info(f"Circuit Breaker '{self.name}' entering HALF_OPEN state.")
                        self.state = "HALF_OPEN"
                        self._probing = True
                    else:
                        raise CircuitBreakerOpenException(
                            f"Circuit Breaker '{self.name}' is OPEN. Target service is degraded."
                        )
                elif self.state == "HALF_OPEN":
                    if self._probing:
                        raise CircuitBreakerOpenException(
                            f"Circuit Breaker '{self.name}' is HALF_OPEN and currently probing."
                        )
                    else:
                        self._probing = True

            try:
                result = func(*args, **kwargs)
                with self._lock:
                    if self.state == "HALF_OPEN":
                        logger.info(f"Circuit Breaker '{self.name}' recovered. Resetting to CLOSED.")
                        self.state = "CLOSED"
                    self.failure_count = 0
                    self._probing = False
                return result
            except Exception as e:
                now_end = time.monotonic()
                with self._lock:
                    self.failure_count += 1
                    self.last_failure_time = now_end
                    self._probing = False
                    if self.failure_count >= self.failure_threshold:
                        logger.error(f"Circuit Breaker '{self.name}' triggered OPEN due to {self.failure_count} consecutive failures: {e}")
                        self.state = "OPEN"
                raise e

        return wrapper
