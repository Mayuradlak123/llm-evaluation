import pybreaker
from .logger import logger

# --- Specialized Fallbacks (Senior Spec) ---
def llm_fallback(*args, **kwargs):
    # Mocking the content object for compatibility
    return type('obj', (object,), {'content': "The AI assistant is currently unavailable due to high load. Please try again in 30 seconds."})

def chroma_fallback(*args, **kwargs):
    logger.error("🛡️ Circuit Breaker: ChromaDB Fallback executed.")
    return None

def neo4j_fallback(*args, **kwargs):
    logger.error("🛡️ Circuit Breaker: Neo4j Fallback executed.")
    return None

# --- Custom Listener for Observability ---
class SeniorCircuitListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        if new_state == pybreaker.STATE_OPEN:
            logger.critical(f"🚨 Circuit {cb.name} TRIP! State -> OPEN. Recovery timeout starting.")
        elif new_state == pybreaker.STATE_HALF_OPEN:
            logger.info(f"🔄 Circuit {cb.name}: Timeout expired. Moving to HALF-OPEN trial.")
        elif new_state == pybreaker.STATE_CLOSED:
            logger.info(f"🟢 Circuit {cb.name} is now CLOSED. Full Recovery.")

# --- Initialize Breakers with proper library implementation ---
llm_breaker = pybreaker.CircuitBreaker(
    fail_max=3, 
    reset_timeout=30, 
    listeners=[SeniorCircuitListener()]
)
llm_breaker.name = "GroqAPI"

chroma_breaker = pybreaker.CircuitBreaker(
    fail_max=3, 
    reset_timeout=60, 
    listeners=[SeniorCircuitListener()]
)
chroma_breaker.name = "ChromaDB"

neo4j_breaker = pybreaker.CircuitBreaker(
    fail_max=3, 
    reset_timeout=30, 
    listeners=[SeniorCircuitListener()]
)
neo4j_breaker.name = "Neo4j"

# Wrapper to handle fallbacks (since pybreaker doesn't have built-in fallback_func in the constructor)
def with_breaker(breaker, fallback_func):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return breaker.call(func, *args, **kwargs)
            except pybreaker.CircuitBreakerError:
                return fallback_func(*args, **kwargs)
        return wrapper
    return decorator
