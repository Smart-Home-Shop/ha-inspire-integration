"""Inspire Home Automation API client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from xml.etree import ElementTree as ET

import aiohttp

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://www.inspirehomeautomation.co.uk/client/api1_4/api.php"

# Status codes from API
STATUS_INVALID_LOGIN = 1
STATUS_USER_NOT_VALIDATED = 2
STATUS_INVALID_KEY = 3
STATUS_GATEWAY_NOT_CONNECTED = 4
STATUS_DEVICE_NOT_CONNECTED = 5
STATUS_INVALID_DEVICE_ID = 6
STATUS_SPECIFY_DEVICE_ID = 8
STATUS_RATE_LIMIT = 11
STATUS_UNIT_ACTIVE = 13
STATUS_MESSAGE_SENT = 14


class InspireAPIError(Exception):
    """Base exception for Inspire API errors."""


class InspireAuthError(InspireAPIError):
    """Authentication error."""


class InspireConnectionError(InspireAPIError):
    """Connection error."""


class InspireRateLimitError(InspireAPIError):
    """Rate limit exceeded."""


class InspireDeviceError(InspireAPIError):
    """Device-specific error."""


class InspireAPIClient:
    """Inspire Home Automation API client."""

    def __init__(
        self,
        api_key: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client.
        
        Args:
            api_key: Inspire API key
            username: Account username
            password: Account password
            session: Optional aiohttp session
        """
        self._api_key = api_key
        self._username = username
        self._password = password
        self._session = session
        self._session_key: str | None = None
        self._owns_session = session is None
        self._last_request_time = 0.0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the API client and cleanup resources."""
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    async def _enforce_rate_limit(self) -> None:
        """Enforce minimum 1 second between requests."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time
        if time_since_last < 1.0:
            await asyncio.sleep(1.0 - time_since_last)
        self._last_request_time = asyncio.get_event_loop().time()

    async def _request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> ET.Element:
        """Make API request and return parsed XML response.
        
        Args:
            method: HTTP method (GET or POST)
            params: Query parameters for GET
            data: Form data for POST
            
        Returns:
            Parsed XML root element
            
        Raises:
            InspireConnectionError: On network errors
            InspireAPIError: On API errors
        """
        await self._enforce_rate_limit()
        
        session = await self._get_session()
        
        try:
            if method == "POST":
                async with session.post(
                    API_BASE_URL,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response.raise_for_status()
                    text = await response.text()
            else:  # GET
                async with session.get(
                    API_BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response.raise_for_status()
                    text = await response.text()
                    
            # Parse XML response
            try:
                root = ET.fromstring(text)
            except ET.ParseError as err:
                _LOGGER.error("Failed to parse XML response: %s", text)
                raise InspireAPIError(f"Invalid XML response: {err}") from err
                
            # Check for error status
            status_elem = root.find(".//status")
            if status_elem is not None:
                code_elem = status_elem.find("code")
                message_elem = status_elem.find("message")
                
                if code_elem is not None and code_elem.text:
                    code = int(code_elem.text)
                    message = message_elem.text if message_elem is not None else "Unknown error"
                    
                    if code in (STATUS_INVALID_LOGIN, STATUS_USER_NOT_VALIDATED):
                        raise InspireAuthError(f"Authentication failed: {message}")
                    elif code == STATUS_INVALID_KEY:
                        # Session key expired, clear it
                        self._session_key = None
                        raise InspireAuthError(f"Session key expired: {message}")
                    elif code in (STATUS_GATEWAY_NOT_CONNECTED, STATUS_DEVICE_NOT_CONNECTED):
                        raise InspireDeviceError(f"Device unavailable: {message}")
                    elif code in (STATUS_INVALID_DEVICE_ID, STATUS_SPECIFY_DEVICE_ID):
                        raise InspireDeviceError(f"Invalid device: {message}")
                    elif code == STATUS_RATE_LIMIT:
                        raise InspireRateLimitError(message)
                    elif code not in (STATUS_UNIT_ACTIVE, STATUS_MESSAGE_SENT):
                        # Unknown error code
                        _LOGGER.warning("Unknown API status code %d: %s", code, message)
                        
            return root
            
        except aiohttp.ClientError as err:
            raise InspireConnectionError(f"Connection failed: {err}") from err

    async def connect(self) -> str:
        """Connect and obtain session key.
        
        Returns:
            Session key
            
        Raises:
            InspireAuthError: On authentication failure
            InspireConnectionError: On connection failure
        """
        data = {
            "action": "connect",
            "apikey": self._api_key,
            "username": self._username,
            "password": self._password,
        }
        
        root = await self._request("POST", data=data)
        
        # Extract session key
        key_elem = root.find(".//key")
        if key_elem is not None and key_elem.text:
            self._session_key = key_elem.text
            _LOGGER.debug("Connected successfully, session key obtained")
            return self._session_key
            
        raise InspireAPIError("No session key returned from connect")

    async def _ensure_connected(self) -> None:
        """Ensure we have a valid session key."""
        if not self._session_key:
            await self.connect()

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get list of all devices.
        
        Returns:
            List of device dictionaries with id, name, type, etc.
            
        Raises:
            InspireAuthError: On authentication failure
            InspireConnectionError: On connection failure
        """
        await self._ensure_connected()
        
        params = {
            "action": "get_devices",
            "key": self._session_key,
            "apikey": self._api_key,
        }
        
        try:
            root = await self._request("GET", params=params)
        except InspireAuthError:
            # Try reconnecting once
            await self.connect()
            params["key"] = self._session_key
            root = await self._request("GET", params=params)
            
        # Parse devices
        devices = []
        devices_elem = root.find(".//devices")
        if devices_elem is not None:
            for device_elem in devices_elem.findall("device"):
                device = {}
                for child in device_elem:
                    device[child.tag] = child.text
                devices.append(device)
                
        return devices

    async def get_device_information(self, device_id: str) -> dict[str, Any]:
        """Get detailed information for a specific device.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device information dictionary
            
        Raises:
            InspireAuthError: On authentication failure
            InspireDeviceError: On device errors
            InspireConnectionError: On connection failure
        """
        await self._ensure_connected()
        
        params = {
            "action": "get_device_information",
            "key": self._session_key,
            "apikey": self._api_key,
            "device_id": device_id,
        }
        
        try:
            root = await self._request("GET", params=params)
        except InspireAuthError:
            # Try reconnecting once
            await self.connect()
            params["key"] = self._session_key
            root = await self._request("GET", params=params)
            
        # Parse device information (flatten one level for nested e.g. Set_Temperatures)
        info = {}
        device_info_elem = root.find(".//Device_Information")
        if device_info_elem is not None:
            for child in device_info_elem:
                if child.text is not None and child.text.strip():
                    info[child.tag] = child.text
                elif len(child) > 0:
                    for sub in child:
                        if sub.text is not None:
                            info[sub.tag] = sub.text
        return info

    async def check_connection(self, device_id: str) -> bool:
        """Check if device is connected.
        
        Args:
            device_id: Device ID
            
        Returns:
            True if device is connected
        """
        await self._ensure_connected()
        
        params = {
            "action": "check_connection",
            "key": self._session_key,
            "apikey": self._api_key,
            "device_id": device_id,
        }
        
        try:
            root = await self._request("GET", params=params)
            # Status code 13 (UNIT_ACTIVE) means connected
            status_elem = root.find(".//status/code")
            if status_elem is not None and status_elem.text:
                return int(status_elem.text) == STATUS_UNIT_ACTIVE
        except (InspireAuthError, InspireDeviceError):
            pass
            
        return False

    async def set_temperature(self, device_id: str, temperature: float) -> None:
        """Set target temperature for device.
        
        Args:
            device_id: Device ID
            temperature: Target temperature (10-30°C, 0.5°C steps)
            
        Raises:
            ValueError: If temperature is out of range
            InspireAuthError: On authentication failure
            InspireConnectionError: On connection failure
        """
        if not 10.0 <= temperature <= 30.0:
            raise ValueError("Temperature must be between 10 and 30°C")
            
        # Round to nearest 0.5
        temperature = round(temperature * 2) / 2
        
        await self._ensure_connected()
        
        data = {
            "action": "send_message",
            "key": self._session_key,
            "apikey": self._api_key,
            "device_id": device_id,
            "message_type": "set_set_point",
            "value": str(temperature),
        }
        
        try:
            await self._request("POST", data=data)
        except InspireAuthError:
            # Try reconnecting once
            await self.connect()
            data["key"] = self._session_key
            await self._request("POST", data=data)

    async def set_function(self, device_id: str, function: int) -> None:
        """Set device function/mode.
        
        Args:
            device_id: Device ID
            function: Function value (1=Off, 2=Program1, 3=Program2, 4=Both, 5=On, 6=Boost)
            
        Raises:
            ValueError: If function is invalid
            InspireAuthError: On authentication failure
            InspireConnectionError: On connection failure
        """
        if function not in (1, 2, 3, 4, 5, 6):
            raise ValueError("Function must be 1-6 (1=Off, 2=Program1, 3=Program2, 4=Both, 5=On, 6=Boost)")
            
        await self._ensure_connected()
        
        data = {
            "action": "send_message",
            "key": self._session_key,
            "apikey": self._api_key,
            "device_id": device_id,
            "message_type": "set_function",
            "value": str(function),
        }
        
        try:
            await self._request("POST", data=data)
        except InspireAuthError:
            # Try reconnecting once
            await self.connect()
            data["key"] = self._session_key
            await self._request("POST", data=data)
