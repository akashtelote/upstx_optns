import logging
import urllib3
from urllib3.util.retry import Retry
import upstox_client

from config.settings import CONNECTION_TIMEOUT, READ_TIMEOUT
from core.auth import authenticate_and_save_token

logger = logging.getLogger(__name__)

def fetch_data_safe(func, *args, **kwargs):
    """
    Wraps API calls in try-except blocks to catch timeouts and return None
    instead of hanging the bot.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Error or timeout during API call {func.__name__}: {e}")
        return None

class UpstoxClient:
    _api_client = None
    _order_api = None

    @classmethod
    def initialize_client(cls, force_refresh: bool = False):
        """
        Initializes the Upstox API client, reloads the token if missing or expired,
        and configures the Retry strategy and timeouts.
        """
        logger.info("Initializing Upstox API client...")
        access_token = authenticate_and_save_token(force_refresh=force_refresh)

        # Set API configuration
        configuration = upstox_client.Configuration()
        configuration.access_token = access_token

        # Initialize the API client
        cls._api_client = upstox_client.ApiClient(configuration)

        # Configure retry strategy and inject custom PoolManager
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )

        timeout = urllib3.Timeout(connect=CONNECTION_TIMEOUT, read=READ_TIMEOUT)

        pool_manager = urllib3.PoolManager(
            num_pools=10,
            maxsize=10,
            block=False,
            retries=retry_strategy,
            timeout=timeout
        )

        # Injecting custom PoolManager to upstox_client.ApiClient's rest_client
        cls._api_client.rest_client.pool_manager = pool_manager

        # Initialize Order API
        cls._order_api = upstox_client.OrderApi(cls._api_client)
        logger.info("Upstox API client initialized successfully.")

    @classmethod
    def get_client(cls):
        """
        Returns the API client and Order API instances.
        Triggers initialization if they are missing.
        """
        if cls._api_client is None or cls._order_api is None:
            cls.initialize_client()
        return cls._api_client, cls._order_api
