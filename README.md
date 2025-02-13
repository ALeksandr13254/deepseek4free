# DeepSeek4Free

A Python package for interacting with the DeepSeek AI chat API. This package provides a clean interface to interact with DeepSeek's chat model, with support for streaming responses, thinking process visibility, and web search capabilities.

> ⚠️ **Service Notice**: DeepSeek API is currently experiencing high load. Work is in progress to integrate additional API providers. Please expect intermittent errors.

> 📝 **Note**: If you encounter any errors, please ensure you are using the latest version of this library. The DeepSeek API may change frequently, and updates are released to maintain compatibility.

## ✨ Features

- 🔄 **Streaming Responses**: Real-time interaction with token-by-token output
- 🤔 **Thinking Process**: Optional visibility into the model's reasoning steps
- 🔍 **Web Search**: Optional integration for up-to-date information
- 💬 **Session Management**: Persistent chat sessions with conversation history
- ⚡ **Efficient PoW**: WebAssembly-based proof of work implementation
- 🛡️ **Error Handling**: Comprehensive error handling with specific exceptions
- ⏱️ **No Timeouts**: Designed for long-running conversations without timeouts
- 🧵 **Thread Support**: Parent message tracking for threaded conversations

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/deepseek4free.git
cd deepseek4free
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🔑 Authentication

To use this package, you need a DeepSeek auth token. Here's how to obtain it:

If you know how to use chrome devtools, simply run this snipped in the console:

```js
JSON.parse(localStorage.getItem("userToken")).value
```

### Method 1: From LocalStorage (Recommended)

<img width="1150" alt="image" src="https://github.com/user-attachments/assets/b4e11650-3d1b-4638-956a-c67889a9f37e" />

1. Visit [chat.deepseek.com](https://chat.deepseek.com)
2. Log in to your account
3. Open browser developer tools (F12 or right-click > Inspect)
4. Go to Application tab (if not visible, click >> to see more tabs)
5. In the left sidebar, expand "Local Storage"
6. Click on "https://chat.deepseek.com"
7. Find the key named `userToken`
8. Copy `"value"` - this is your authentication token

### Method 2: From Network Tab

Alternatively, you can get the token from network requests:

1. Visit [chat.deepseek.com](https://chat.deepseek.com)
2. Log in to your account
3. Open browser developer tools (F12)
4. Go to Network tab
5. Make any request in the chat
6. Find the request headers
7. Copy the `authorization` token (without 'Bearer ' prefix)

### Handling Cloudflare Challenges

If you encounter Cloudflare challenges ("Just a moment..." page), you'll need to get a `cf_clearance` cookie. Run this command:

```bash
python -m dsk.bypass
```

This will:
1. Open an undetected browser
2. Visit DeepSeek and solve the Cloudflare challenge
3. Capture and save the `cf_clearance` cookie
4. The cookie will be automatically used in future requests

You only need to run this when:
- You get Cloudflare challenges in your requests
- Your existing cf_clearance cookie expires
- You see the error "Please wait a few minutes before trying again"

The captured cookie will be stored in `dsk/cookies.json` and automatically used by the API.

## 📚 Usage

### Basic Example

```python
import asyncio
from dsk.api import DeepSeekAPI

async_prompt = "What is Python?"

async def main():
    api = DeepSeekAPI(auth_token="YOUR_AUTH_TOKEN")
    chat_id = await api.create_chat_session()
    print(f"chat_id: {chat_id}")

    async for chunk in api.chat_completion(chat_id, async_prompt, thinking_enabled=False, search_enabled=False):
        print(chunk.get('content', ''), end='')

asyncio.run(main())
```