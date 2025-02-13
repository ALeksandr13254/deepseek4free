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