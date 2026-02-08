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
STATUS_NO_LOG_DATA = 23


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
        action = (params or {}).get("action") or (data or {}).get("action")
        device_id = (params or {}).get("device_id") or (data or {}).get("device_id")
        desc = f"{method} action={action}"
        if device_id:
            desc += f" device_id={device_id}"
        _LOGGER.debug("Request: %s", desc)

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
                    elif code == STATUS_NO_LOG_DATA:
                        # No log data found - acceptable for get_log
                        pass
                    elif code not in (STATUS_UNIT_ACTIVE, STATUS_MESSAGE_SENT):
                        # Unknown error code
                        _LOGGER.warning("Unknown API status code %d: %s", code, message)
                        
            _LOGGER.debug("Request: %s -> success", desc)
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

    async def get_summary(self) -> dict[str, Any]:
        """Get system summary/statistics.

        Returns:
            Summary dictionary (structure depends on API response).

        Raises:
            InspireAuthError: On authentication failure
            InspireConnectionError: On connection failure
        """
        await self._ensure_connected()

        params = {
            "action": "get_summary",
            "key": self._session_key,
            "apikey": self._api_key,
        }

        try:
            root = await self._request("GET", params=params)
        except InspireAuthError:
            await self.connect()
            params["key"] = self._session_key
            root = await self._request("GET", params=params)

        summary: dict[str, Any] = {}
        summary_elem = root.find(".//summary")
        if summary_elem is not None:
            for child in summary_elem:
                if child.text is not None and child.text.strip():
                    summary[child.tag] = child.text
                elif len(child) > 0:
                    summary[child.tag] = [
                        {sub.tag: (sub.text or "") for sub in item}
                        for item in child
                    ]
        return summary

    async def check_confirms(self, device_id: str) -> list[dict[str, Any]]:
        """Check message delivery confirmation status for a device.

        Args:
            device_id: Device ID

        Returns:
            List of confirmation records.

        Raises:
            InspireAuthError: On authentication failure
            InspireDeviceError: On device errors
            InspireConnectionError: On connection failure
        """
        await self._ensure_connected()

        params = {
            "action": "check_confirms",
            "key": self._session_key,
            "apikey": self._api_key,
            "device_id": device_id,
        }

        try:
            root = await self._request("GET", params=params)
        except InspireAuthError:
            await self.connect()
            params["key"] = self._session_key
            root = await self._request("GET", params=params)

        confirms: list[dict[str, Any]] = []
        confirms_elem = root.find(".//confirms")
        if confirms_elem is not None:
            for item in confirms_elem.findall("confirm") or confirms_elem:
                rec = {}
                for child in item:
                    if child.text is not None:
                        rec[child.tag] = child.text
                if rec:
                    confirms.append(rec)
        return confirms

    async def get_log(self, device_id: str) -> list[dict[str, Any]]:
        """Retrieve device logs/diagnostics.

        Args:
            device_id: Device ID

        Returns:
            List of log entries.

        Raises:
            InspireAuthError: On authentication failure
            InspireDeviceError: On device errors
            InspireConnectionError: On connection failure
        """
        await self._ensure_connected()

        params = {
            "action": "get_log",
            "key": self._session_key,
            "apikey": self._api_key,
            "device_id": device_id,
        }

        try:
            root = await self._request("GET", params=params)
        except InspireAuthError:
            await self.connect()
            params["key"] = self._session_key
            root = await self._request("GET", params=params)

        status_elem = root.find(".//status/code")
        if status_elem is not None and status_elem.text and int(status_elem.text) == STATUS_NO_LOG_DATA:
            return []

        log_entries: list[dict[str, Any]] = []
        log_elem = root.find(".//log") or root.find(".//Log")
        if log_elem is not None:
            for item in log_elem.findall("entry") or log_elem.findall("item") or list(log_elem):
                if item.tag in ("entry", "item") or item.text or len(item) > 0:
                    rec = {}
                    for child in item:
                        if child.text is not None:
                            rec[child.tag] = child.text
                    if rec:
                        log_entries.append(rec)
        return log_entries

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

    def _send_message(
        self, device_id: str, message_type: str, value: str | None = None, **extra: Any
    ) -> dict[str, Any]:
        """Build send_message payload (caller uses _request)."""
        data: dict[str, Any] = {
            "action": "send_message",
            "key": self._session_key,
            "apikey": self._api_key,
            "device_id": device_id,
            "message_type": message_type,
        }
        if value is not None:
            data["value"] = value
        data.update(extra)
        return data

    async def _post_message(
        self, device_id: str, message_type: str, value: str | None = None, **extra: Any
    ) -> None:
        """Send a message and handle auth reconnect."""
        await self._ensure_connected()
        data = self._send_message(device_id, message_type, value=value, **extra)
        try:
            await self._request("POST", data=data)
        except InspireAuthError:
            await self.connect()
            data["key"] = self._session_key
            await self._request("POST", data=data)

    async def set_time(self, device_id: str, time_str: str) -> None:
        """Synchronize device clock.

        Args:
            device_id: Device ID
            time_str: Time value (format as required by API, e.g. ISO or HH:MM)

        Raises:
            InspireAuthError: On authentication failure
            InspireConnectionError: On connection failure
        """
        await self._post_message(device_id, "set_time", value=time_str)

    async def set_program_time(
        self,
        device_id: str,
        program: int,
        day: int,
        period: int,
        time_str: str,
        temperature: float,
    ) -> None:
        """Configure a program schedule slot.

        Args:
            device_id: Device ID
            program: Program number (1 or 2)
            day: Day index (0-6 or as per API)
            period: Period index within the day
            time_str: Time for the period (e.g. HH:MM)
            temperature: Set point for the period (10-30°C, 0.5 steps)

        Raises:
            ValueError: If temperature is out of range
            InspireAuthError: On authentication failure
            InspireConnectionError: On connection failure
        """
        if not 10.0 <= temperature <= 30.0:
            raise ValueError("Temperature must be between 10 and 30°C")
        temperature = round(temperature * 2) / 2
        value = f"{program},{day},{period},{time_str},{temperature}"
        await self._post_message(device_id, "set_program_time", value=value)

    async def set_scheduled_start(self, device_id: str, datetime_str: str) -> None:
        """Schedule heating start time.

        Args:
            device_id: Device ID
            datetime_str: Date/time for scheduled start (format as per API)

        Raises:
            InspireAuthError: On authentication failure
            InspireConnectionError: On connection failure
        """
        await self._post_message(device_id, "set_scheduled_start", value=datetime_str)

    async def cancel_scheduled_start(self, device_id: str) -> None:
        """Cancel scheduled heating start.

        Args:
            device_id: Device ID

        Raises:
            InspireAuthError: On authentication failure
            InspireConnectionError: On connection failure
        """
        await self._post_message(device_id, "cancel_scheduled_start")

    async def set_pgmtype(self, device_id: str, program_type: str | int) -> None:
        """Set program type.

        Args:
            device_id: Device ID
            program_type: Program type (value or code as per API)

        Raises:
            InspireAuthError: On authentication failure
            InspireConnectionError: On connection failure
        """
        await self._post_message(
            device_id, "set_pgmtype", value=str(program_type)
        )

    async def set_advance(self, device_id: str) -> None:
        """Advance to next program period.

        Args:
            device_id: Device ID

        Raises:
            InspireAuthError: On authentication failure
            InspireConnectionError: On connection failure
        """
        await self._post_message(device_id, "set_advance")
