import logging
import os
import json
import requests

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
    def __init__(self):
        """
        Initializes the Upstox API client by loading the access token.
        If the token file is missing or invalid, it triggers authentication.
        """
        self.access_token = None
        token_file = "config/token.json"

        try:
            if os.path.exists(token_file):
                with open(token_file, "r") as f:
                    token_data = json.load(f)
                    self.access_token = token_data.get("access_token")

            if not self.access_token:
                logger.info("Access token missing or invalid. Triggering authentication.")
                self.access_token = authenticate_and_save_token(force_refresh=False)

        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read token file: {e}. Triggering authentication.")
            self.access_token = authenticate_and_save_token(force_refresh=False)

    def _get_instrument_token(self, symbol: str) -> str:
        """
        Helper method to get instrument token. Currently returns a mock value.
        Will be replaced with real database lookup later.
        """
        return f"NSE_EQ|{symbol}"

    def place_order(self, symbol: str, side: str, quantity: int, price: float, is_live: bool = False):
        """
        Places an order or routes a paper trade.
        """
        if not is_live:
            logger.info(f"Successfully routed PAPER trade: {side} {quantity} {symbol} @ ₹{price}")
            return "PAPER_ORDER_123"

        url = "https://api.upstox.com/v2/order/place"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        payload = {
            "quantity": quantity,
            "product": "DELIVERY",
            "validity": "DAY",
            "price": price,
            "instrument_token": self._get_instrument_token(symbol),
            "order_type": "LIMIT",
            "transaction_type": side.upper()
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"Upstox API Error: {response.text}")
                return None

            data = response.json()
            return data.get("data", {}).get("order_id")

        except Exception as e:
            logger.error(f"Exception during live order placement: {e}")
            return None
