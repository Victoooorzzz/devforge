import os, httpx, asyncio
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('LEMONSQUEEZY_API_KEY')

async def test():
    headers = {
        'Accept': 'application/vnd.api+json',
        'Authorization': f'Bearer {api_key}'
    }
    async with httpx.AsyncClient() as client:
        r = await client.get('https://api.lemonsqueezy.com/v1/variants', headers=headers)
        data = r.json()
        if 'data' in data:
            for variant in data['data']:
                print(f"Variant ID: {variant['id']}, Product ID: {variant['attributes']['product_id']}, Name: {variant['attributes']['name']}")
        else:
            print(data)

asyncio.run(test())
