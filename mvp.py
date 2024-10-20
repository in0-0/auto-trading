import json
import os

import openai
import pyupbit
import requests
from dotenv import load_dotenv

load_dotenv()

# 1. upbit chart data fetching
df = pyupbit.get_ohlcv("KRW-BTC", count=30)
chart_data_json = df.to_json()
print(chart_data_json)

# 2. Fetch Bitcoin-related news using a news API
news_api_key = os.getenv("NEWS_API_KEY")
news_query = "bitcoin"
news_url = f"https://newsapi.org/v2/everything?q={news_query}&apiKey={news_api_key}"
response_news = requests.get(news_url)

if response_news.status_code == 200:
    news_data = response_news.json()
    articles = news_data.get("articles", [])
    news_summary = "\n".join(
        [f"- {article['title']}: {article['description']}" for article in articles[:5]]
    )
else:
    news_summary = "No news data available"

# 3. Get a decision from AI based on the chart data and news
openai.api_key = os.getenv("OPENAI_API_KEY")

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": (
                "You're an expert in Bitcoin investing. Tell users whether they should buy, sell, or hold "
                "based on the chart data and recent news provided.\n\nResponse Json Example:\n"
                '{"decision": "buy", "reason": "Reason why AI thinks like that"}\n'
                '{"decision": "sell", "reason": "Reason why AI thinks like that"}\n'
                '{"decision": "hold", "reason": "Reason why AI thinks like that"}'
            ),
        },
        {
            "role": "user",
            "content": f"Chart Data: {chart_data_json}\n\nRecent News:\n{news_summary}",
        },
    ],
)

try:
    result = json.loads(response["choices"][0]["message"]["content"])
except (json.JSONDecodeError, KeyError) as e:
    raise Exception("Unexpected response format from OpenAI") from e

# 4. Execute trade decision using Upbit API
access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")
upbit = pyupbit.Upbit(access, secret)

decision = result.get("decision", "").lower()

if decision == "buy":
    print("buy")
    krw_balance = upbit.get_balance("KRW")
    print(upbit.buy_market_order("KRW-BTC", krw_balance))
elif decision == "sell":
    print("sell")
    btc_balance = upbit.get_balance("BTC")
    print(upbit.sell_market_order("KRW-BTC", btc_balance))
elif decision == "hold":
    print("hold")
else:
    raise Exception("Invalid decision received from AI")
