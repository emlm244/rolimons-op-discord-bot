"""Roblox Economy API client for fetching resellers and executing purchases."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import aiohttp

from src.config import config
from src.data.models import Listing

logger = logging.getLogger(__name__)


class PurchaseResult(Enum):
    """Result of a purchase attempt."""

    SUCCESS = "success"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    LISTING_GONE = "listing_gone"
    ALREADY_OWNED = "already_owned"
    RATE_LIMITED = "rate_limited"
    AUTH_FAILED = "auth_failed"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ResaleData:
    """Resale data for an item from Roblox API."""

    asset_id: int
    asset_stock: Optional[int] = None
    sales: int = 0
    number_remaining: Optional[int] = None
    recent_average_price: int = 0
    original_price: Optional[int] = None


@dataclass
class PurchaseResponse:
    """Response from a purchase attempt."""

    result: PurchaseResult
    message: str = ""
    purchased_at: Optional[datetime] = None
    transaction_id: Optional[str] = None


class RobloxClient:
    """Async client for Roblox Economy API.

    Handles:
    - XSRF token management
    - Reseller listings
    - Item purchases
    - Resale data
    """

    def __init__(self, roblosecurity: Optional[str] = None) -> None:
        """Initialize client.

        Args:
            roblosecurity: The .ROBLOSECURITY cookie for authentication.
                          Uses config value if not provided.
        """
        self._roblosecurity = roblosecurity or config.roblosecurity
        self._session: Optional[aiohttp.ClientSession] = None
        self._xsrf_token: Optional[str] = None
        self._xsrf_expires: Optional[datetime] = None
        self._xsrf_ttl_seconds = 300  # Refresh every 5 minutes

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create authenticated HTTP session."""
        if self._session is None or self._session.closed:
            cookies = {".ROBLOSECURITY": self._roblosecurity}
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                cookies=cookies,
                headers={"User-Agent": "RISniper/1.0"},
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _refresh_xsrf(self, force: bool = False) -> Optional[str]:
        """Refresh XSRF token.

        The XSRF token is obtained by making a request that triggers
        a 403 response with the token in the x-csrf-token header.

        Args:
            force: Force refresh even if token is still valid.

        Returns:
            The XSRF token, or None if refresh failed.
        """
        now = datetime.utcnow()

        # Check if we need to refresh
        if (
            not force
            and self._xsrf_token
            and self._xsrf_expires
            and now < self._xsrf_expires
        ):
            return self._xsrf_token

        session = await self._get_session()

        try:
            # Make a POST request that will fail with 403 but return token
            async with session.post(
                f"{config.roblox_auth_url}/v1/logout"
            ) as response:
                # The token is returned in header regardless of status
                token = response.headers.get("x-csrf-token")
                if token:
                    self._xsrf_token = token
                    self._xsrf_expires = datetime.utcnow()
                    # Token is valid for a while, but we refresh frequently
                    logger.debug("XSRF token refreshed")
                    return token

        except aiohttp.ClientError as e:
            logger.error(f"Failed to refresh XSRF token: {e}")

        return self._xsrf_token

    async def get_resellers(
        self,
        asset_id: int,
        limit: int = 10,
    ) -> list[Listing]:
        """Get current resellers for an item.

        Args:
            asset_id: The Roblox asset ID.
            limit: Maximum number of listings to return.

        Returns:
            List of Listing objects sorted by price (lowest first).
        """
        session = await self._get_session()
        url = f"{config.roblox_economy_url}/v1/assets/{asset_id}/resellers"

        try:
            params = {"limit": limit}
            async with session.get(url, params=params) as response:
                if response.status == 400:
                    # Item might not be resellable
                    return []
                if response.status != 200:
                    logger.error(f"Resellers API error: {response.status}")
                    return []

                data = await response.json()
                listings = []

                for item in data.get("data", []):
                    seller = item.get("seller", {})
                    listings.append(
                        Listing(
                            item_id=asset_id,
                            seller_id=seller.get("id", 0),
                            seller_name=seller.get("name", "Unknown"),
                            price=item.get("price", 0),
                            product_id=item.get("productId", 0),
                            serial_number=item.get("serialNumber"),
                        )
                    )

                return sorted(listings, key=lambda x: x.price)

        except asyncio.TimeoutError:
            logger.error("Resellers API request timed out")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"Resellers API client error: {e}")
            return []

    async def get_resale_data(self, asset_id: int) -> Optional[ResaleData]:
        """Get resale data for an item (RAP, sales, stock).

        Args:
            asset_id: The Roblox asset ID.

        Returns:
            ResaleData object, or None if not available.
        """
        session = await self._get_session()
        url = f"{config.roblox_economy_url}/v1/assets/{asset_id}/resale-data"

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                return ResaleData(
                    asset_id=asset_id,
                    asset_stock=data.get("assetStock"),
                    sales=data.get("sales", 0),
                    number_remaining=data.get("numberRemaining"),
                    recent_average_price=data.get("recentAveragePrice", 0),
                    original_price=data.get("originalPrice"),
                )

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.error(f"Resale data API error: {e}")
            return None

    async def purchase(
        self,
        product_id: int,
        expected_price: int,
        expected_seller_id: int,
    ) -> PurchaseResponse:
        """Execute a purchase.

        Args:
            product_id: The product ID from the listing.
            expected_price: The price we expect to pay.
            expected_seller_id: The seller ID we expect.

        Returns:
            PurchaseResponse with result and details.
        """
        if not self._roblosecurity:
            return PurchaseResponse(
                result=PurchaseResult.AUTH_FAILED,
                message="ROBLOSECURITY cookie not configured",
            )

        # Refresh XSRF token
        xsrf = await self._refresh_xsrf()
        if not xsrf:
            return PurchaseResponse(
                result=PurchaseResult.AUTH_FAILED,
                message="Failed to obtain XSRF token",
            )

        session = await self._get_session()
        url = f"{config.roblox_economy_url}/v1/purchases/products/{product_id}"

        payload = {
            "expectedCurrency": 1,  # Robux
            "expectedPrice": expected_price,
            "expectedSellerId": expected_seller_id,
        }

        headers = {
            "X-CSRF-TOKEN": xsrf,
            "Content-Type": "application/json",
        }

        try:
            async with session.post(url, json=payload, headers=headers) as response:
                # Handle XSRF token refresh
                if response.status == 403:
                    new_token = response.headers.get("x-csrf-token")
                    if new_token:
                        self._xsrf_token = new_token
                        # Retry with new token
                        headers["X-CSRF-TOKEN"] = new_token
                        async with session.post(
                            url, json=payload, headers=headers
                        ) as retry_response:
                            return await self._parse_purchase_response(retry_response)

                    return PurchaseResponse(
                        result=PurchaseResult.AUTH_FAILED,
                        message="XSRF token expired and refresh failed",
                    )

                return await self._parse_purchase_response(response)

        except asyncio.TimeoutError:
            return PurchaseResponse(
                result=PurchaseResult.UNKNOWN_ERROR,
                message="Purchase request timed out",
            )
        except aiohttp.ClientError as e:
            return PurchaseResponse(
                result=PurchaseResult.UNKNOWN_ERROR,
                message=f"Network error: {e}",
            )

    async def _parse_purchase_response(
        self, response: aiohttp.ClientResponse
    ) -> PurchaseResponse:
        """Parse the purchase API response."""
        try:
            data = await response.json()
        except Exception:
            data = {}

        if response.status == 200:
            return PurchaseResponse(
                result=PurchaseResult.SUCCESS,
                message="Purchase successful",
                purchased_at=datetime.utcnow(),
                transaction_id=str(data.get("transactionId", "")),
            )

        # Handle specific error cases
        error_msg = data.get("message", "") or data.get("errors", [{}])[0].get(
            "message", "Unknown error"
        )

        if response.status == 400:
            if "InsufficientFunds" in error_msg or "insufficient" in error_msg.lower():
                return PurchaseResponse(
                    result=PurchaseResult.INSUFFICIENT_FUNDS,
                    message=error_msg,
                )
            if "AlreadyOwned" in error_msg or "already own" in error_msg.lower():
                return PurchaseResponse(
                    result=PurchaseResult.ALREADY_OWNED,
                    message=error_msg,
                )
            if "NotForSale" in error_msg or "not for sale" in error_msg.lower():
                return PurchaseResponse(
                    result=PurchaseResult.LISTING_GONE,
                    message=error_msg,
                )

        if response.status == 429:
            return PurchaseResponse(
                result=PurchaseResult.RATE_LIMITED,
                message="Rate limited by Roblox",
            )

        if response.status in (401, 403):
            return PurchaseResponse(
                result=PurchaseResult.AUTH_FAILED,
                message=error_msg,
            )

        return PurchaseResponse(
            result=PurchaseResult.UNKNOWN_ERROR,
            message=f"HTTP {response.status}: {error_msg}",
        )

    async def get_user_balance(self) -> Optional[int]:
        """Get the authenticated user's Robux balance.

        Returns:
            Robux balance, or None if request failed.
        """
        session = await self._get_session()
        url = f"{config.roblox_economy_url}/v1/user/currency"

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                return data.get("robux", 0)
        except (asyncio.TimeoutError, aiohttp.ClientError):
            return None

    async def verify_auth(self) -> bool:
        """Verify that authentication is working.

        Returns:
            True if authenticated, False otherwise.
        """
        balance = await self.get_user_balance()
        return balance is not None
