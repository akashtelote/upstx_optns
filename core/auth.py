import os
import json
import logging
from datetime import datetime, timezone, timedelta
from filelock import FileLock
from upstox_totp.client import UpstoxTOTP
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

TOKEN_FILE = "data/token.json"
LOCK_FILE = "data/token.json.lock"

# 12 hours in seconds
TOKEN_MAX_AGE_SECONDS = 12 * 3600
# 5 minutes in seconds
TOKEN_FORCE_REFRESH_GUARD_SECONDS = 300

def get_current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

def authenticate_and_save_token(force_refresh: bool = False) -> str:
    """
    Thread-safe function to authenticate with Upstox API and save the token.
    Uses FileLock to prevent multiple processes from refreshing the token simultaneously.
    If force_refresh is True, it will try to get a new token unless the token was created
    within the force-refresh guard interval (e.g., 300 seconds).
    """
    load_dotenv()

    # Ensure data directory exists
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)

    lock = FileLock(LOCK_FILE)

    with lock:
        current_time = datetime.now(timezone.utc)

        # 1. Check existing token
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "r") as f:
                    data = json.load(f)

                access_token = data.get("access_token")
                created_at_str = data.get("created_at")

                if access_token and created_at_str:
                    created_at = datetime.fromisoformat(created_at_str)
                    age_seconds = (current_time - created_at).total_seconds()

                    if age_seconds < TOKEN_FORCE_REFRESH_GUARD_SECONDS:
                        logger.warning(f"Token is very new ({age_seconds:.1f}s old). Prevented OTP spam. Ignoring force_refresh if set.")
                        return access_token

                    if not force_refresh and age_seconds < TOKEN_MAX_AGE_SECONDS:
                        logger.info("Using existing token (less than 12 hours old).")
                        return access_token
            except Exception as e:
                logger.error(f"Error reading token file: {e}. A new token will be generated.")

        # 2. Fetch new token
        logger.info("Generating new Upstox token...")

        username = os.environ.get("UPSTOX_USER_ID")
        password = os.environ.get("UPSTOX_PASSWORD")
        pin_code = os.environ.get("UPSTOX_PIN_CODE")
        totp_secret = os.environ.get("UPSTOX_TOTP_SECRET")
        client_id = os.environ.get("UPSTOX_API_KEY")
        client_secret = os.environ.get("UPSTOX_API_SECRET")
        redirect_uri = os.environ.get("UPSTOX_REDIRECT_URI")

        if not all([username, password, pin_code, totp_secret, client_id, client_secret, redirect_uri]):
            logger.error("Missing required Upstox environment variables.")
            raise ValueError("Missing required Upstox environment variables.")

        try:
            client = UpstoxTOTP(
                username=username,
                password=password,
                pin_code=pin_code,
                totp_secret=totp_secret,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri
            )

            # Using UpstoxTOTP to fetch token
            # Note: app_token is the property, get_access_token returns AccessTokenResponse
            token_response = client.app_token.get_access_token()

            if not token_response.success or not token_response.data:
                raise RuntimeError(f"Failed to fetch token, response not successful: {token_response.error}")

            new_access_token = token_response.data.access_token

            if not new_access_token:
                 raise RuntimeError(f"Could not extract access token from response: {token_response.model_dump()}")

            # Save the new token
            token_data = {
                "access_token": new_access_token,
                "created_at": current_time.isoformat()
            }

            with open(TOKEN_FILE, "w") as f:
                json.dump(token_data, f, indent=4)

            logger.info("Successfully generated and saved new token.")
            return new_access_token

        except Exception as e:
            logger.error(f"Failed to authenticate with Upstox: {e}")
            raise
