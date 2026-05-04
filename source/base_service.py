from srsly import json_loads
from typing import Any
import sys
from loguru import logger
from asyncio import Lock

# Hapus konfigurasi default
logger.remove()
# Tambahkan handler baru yang hanya fokus pada project kamu
logger.add(
    sys.stderr, 
    format="<green>{time}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    backtrace=False, # Matikan backtrace yang terlalu dalam
    diagnose=True    # Biarkan tetap menunjukkan nilai variabel yang error
)

def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {column: value for column, value in zip(fields, row)}

class RawResponse:
    def __init__(self, status_code: int, content: bytes):
        self.content = content
        self.status_code = status_code
    
    
    def text(self) -> str:
        return self.content.decode("utf-8")
    
    def json(self) -> dict[str, Any] | list[Any]:
        return json_loads(self.content)

        

class BaseService:
    def __init__(self, client_headers: dict[str, str] | None = None, client_cookies: dict[str, str] | None = None, timeout: int = 30):
        self.client_headers = client_headers
        self.client_cookies = client_cookies
        self.timeout = timeout
        self._initialized = False
        self._lock = None
    
    async def start(self):
        from httpx import AsyncClient
        self.client = AsyncClient(headers=self.client_headers, cookies=self.client_cookies, follow_redirects=True, max_redirects=10, timeout=self.timeout, trust_env=True, http1=True, http2=False, verify=False)
    
    async def client_get(self, url: str, params: dict[str, str] = {}) -> RawResponse:
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return RawResponse(response.status_code, await response.aread())
    
    async def ensure_started(self):
        if self._lock is None:
            self._lock = Lock()
        async with self._lock:
            if not self._initialized:
                logger.info("Service starting...")
                await self.start()

                self._initialized = True
                logger.info("Service started.")

    async def close(self):
        await self.client.aclose()
    