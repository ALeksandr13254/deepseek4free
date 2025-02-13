from curl_cffi.requests import AsyncSession
from typing import Optional, Dict, Any, AsyncGenerator, Literal
import json
from .pow import DeepSeekPOW
import sys
from pathlib import Path
import asyncio

ThinkingMode = Literal['detailed', 'simple', 'disabled']
SearchMode = Literal['enabled', 'disabled']

class DeepSeekError(Exception):
    """Base exception for all DeepSeek API errors"""
    pass

class AuthenticationError(DeepSeekError):
    """Raised when authentication fails"""
    pass

class RateLimitError(DeepSeekError):
    """Raised when API rate limit is exceeded"""
    pass

class NetworkError(DeepSeekError):
    """Raised when network communication fails"""
    pass

class CloudflareError(DeepSeekError):
    """Raised when Cloudflare blocks the request"""
    pass

class APIError(DeepSeekError):
    """Raised when API returns an error response"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

class DeepSeekAPI:
    BASE_URL = "https://chat.deepseek.com/api/v0"

    def __init__(self, auth_token: str):
        if auth_token == "YOUR_AUTH_TOKEN" or not auth_token or not isinstance(auth_token, str):
            raise AuthenticationError("Invalid auth token provided")

        self.auth_token = auth_token
        self.pow_solver = DeepSeekPOW()
        self.cookies = self._load_cookies()

    def _load_cookies(self) -> Dict:
        cookies_path = Path(__file__).parent / 'cookies.json'
        try:
            with open(cookies_path, 'r') as f:
                return json.load(f).get('cookies', {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"\033[93mWarning: Could not load cookies from {cookies_path}: {e}\033[0m", file=sys.stderr)
            return {}

    def _get_headers(self, pow_response: Optional[str] = None) -> Dict[str, str]:
        headers = {
            'accept': '*/*',
            'accept-language': 'en,fr-FR;q=0.9,fr;q=0.8,es-ES;q=0.7,es;q=0.6,en-US;q=0.5,am;q=0.4,de;q=0.3',
            'authorization': f'Bearer {self.auth_token}',
            'content-type': 'application/json',
            'origin': 'https://chat.deepseek.com',
            'referer': 'https://chat.deepseek.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'x-app-version': '20241129.1',
            'x-client-locale': 'en_US',
            'x-client-platform': 'web',
            'x-client-version': '1.0.0-always',
        }

        if pow_response:
            headers['x-ds-pow-response'] = pow_response

        return headers

    async def _refresh_cookies(self) -> None:
        """Асинхронное обновление cookies"""
        try:
            script_path = Path(__file__).parent / 'bypass.py'
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.wait()
            await asyncio.sleep(2)
            self.cookies = self._load_cookies()
        except Exception as e:
            print(f"\033[93mWarning: Failed to refresh cookies: {e}\033[0m", file=sys.stderr)

    async def _make_request(self, method: str, endpoint: str, json_data: Dict[str, Any], pow_required: bool = False) -> Any:
        url = f"{self.BASE_URL}{endpoint}"

        retry_count = 0
        max_retries = 2

        async with AsyncSession() as session:
            while retry_count < max_retries:
                try:
                    headers = self._get_headers()
                    if pow_required:
                        challenge = await self._get_pow_challenge()
                        headers = self._get_headers(self.pow_solver.solve_challenge(challenge))

                    response = await session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=json_data,
                        cookies=self.cookies,
                        impersonate='chrome120',
                        timeout=None
                    )

                    # Check if we hit Cloudflare protection
                    if "<!DOCTYPE html>" in response.text and "Just a moment" in response.text:
                        print("\033[93mWarning: Cloudflare protection detected. Bypassing...\033[0m", file=sys.stderr)
                        if retry_count < max_retries - 1:
                            await self._refresh_cookies()  # Refresh cookies
                            retry_count += 1
                            continue

                    # Handle other response codes
                    if response.status_code != 200:
                        await self._handle_errors(response)

                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        raise APIError("Invalid JSON response")

                except Exception as e:
                    if retry_count < max_retries - 1:
                        retry_count += 1
                        continue
                    raise

            raise APIError("Failed to bypass Cloudflare protection after multiple attempts")

    async def _get_pow_challenge(self) -> Dict[str, Any]:
        response = await self._make_request(
            'POST',
            '/chat/create_pow_challenge',
            {'target_path': '/api/v0/chat/completion'}
        )
        if not isinstance(response, dict):
            raise APIError("Invalid challenge response format from server")
        try:
            return response['data']['biz_data']['challenge']
        except (KeyError, TypeError):
            raise APIError("Missing required fields in challenge response")

    async def create_chat_session(self) -> str:
        """Creates a new chat session and returns the session ID"""
        response = await self._make_request(
            'POST',
            '/chat_session/create',
            {'character_id': None}
        )
        if not isinstance(response, dict):
            raise APIError("Invalid session creation response format from server")
        try:
            return response['data']['biz_data']['id']
        except (KeyError, TypeError):
            raise APIError("Missing required fields in session creation response")

    async def _handle_errors(self, response):
        """Error handling"""
        try:
            error_data = await response.json()
            msg = error_data.get("message", "Unknown error")

            if response.status_code == 422:
                details = error_data.get("details", {})
                msg += f" | Details: {json.dumps(details)}"

        except json.JSONDecodeError:
            msg = f"HTTP Error {response.status_code}"

        if response.status_code == 401:
            raise AuthenticationError(msg)
        elif response.status_code == 422:
            raise APIError(f"Validation error: {msg}", response.status_code)
        elif response.status_code == 429:
            raise RateLimitError(f"RateLimit error: {msg}", response.status_code)
        elif 500 <= response.status_code < 600:
            raise APIError(f"Server error: {msg}", response.status_code)
        else:
            raise APIError(f"API error: {msg}", response.status_code)

    async def chat_completion(self,
                            chat_session_id: str,
                            prompt: str,
                            parent_message_id: Optional[str] = None,
                            thinking_enabled: bool = True,
                            search_enabled: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """Send a message and get streaming response"""
        if not prompt or not isinstance(prompt, str):
            raise ValueError("Prompt must be a non-empty string")
        if not chat_session_id or not isinstance(chat_session_id, str):
            raise ValueError("Chat session ID must be a non-empty string")

        json_data = {
            'chat_session_id': chat_session_id,
            'parent_message_id': parent_message_id,
            'prompt': prompt,
            'ref_file_ids': [],
            'thinking_enabled': thinking_enabled,
            'search_enabled': search_enabled,
        }

        async with AsyncSession() as session:
            response = await session.post(
                f"{self.BASE_URL}/chat/completion",
                headers=self._get_headers(pow_response=await self._get_pow_header()),
                json=json_data,
                cookies=self.cookies,
                impersonate='chrome120',
                stream=True,
                timeout=None
            )

            if response.status_code != 200:
                await self._handle_errors(response)

            async for chunk in response.aiter_lines():
                try:
                    data = self._parse_chunk(chunk)
                    if data:
                        yield data
                        if data.get('finish_reason') == 'stop':
                            break
                except Exception as e:
                    raise APIError(f"Error parsing response chunk: {str(e)}")

    async def _get_pow_header(self) -> str:
        challenge = await self._get_pow_challenge()
        return self.pow_solver.solve_challenge(challenge)

    def _parse_chunk(self, chunk: bytes) -> Optional[Dict[str, Any]]:
        """Parse a SSE chunk from the API response"""
        if not chunk:
            return None

        try:
            if chunk.startswith(b'data: '):
                data = json.loads(chunk[6:])

                if 'choices' in data and data['choices']:
                    choice = data['choices'][0]
                    if 'delta' in choice:
                        delta = choice['delta']

                        return {
                            'content': delta.get('content', ''),
                            'type': delta.get('type', ''),
                            'finish_reason': choice.get('finish_reason')
                        }
        except json.JSONDecodeError:
            raise APIError("Invalid JSON in response chunk")
        except Exception as e:
            raise APIError(f"Error parsing chunk: {str(e)}")

        return None