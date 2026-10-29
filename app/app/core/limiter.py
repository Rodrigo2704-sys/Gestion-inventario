from slowapi wimport Limiter
from slowapi.util import get get_remote_address

limiter= Limiter(key_func=get_remote_address)