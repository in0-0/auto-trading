# 2. Fetch Bitcoin-related news using a news API
import os
from datetime import datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

today = datetime.now()
today_str = today.isoformat(timespec="seconds")
print(today)
timestamp = "timestamp.txt"


def get_last_timestamp():
    if os.path.exists(timestamp):
        with open(timestamp, "r") as f:
            timestamp_str = f.read().strip()
            last_date = datetime.fromisoformat(timestamp_str)
            print((last_date - timedelta(hours=4)))
            from_data = (last_date - timedelta(2)).isoformat(timespec="seconds")
            return from_data
    return datetime.now().isoformat(timespec="seconds")


# 타임스탬프 저장
def save_timestamp():
    with open(timestamp, "w") as f:
        timedelta(7)
        f.write(today.isoformat(timespec="seconds"))


def get_news_summary():
    news_api_key = os.getenv("NEWS_API_KEY")
    news_query = "bitcoin"
    news_url = f"https://newsapi.org/v2/everything?q={news_query}&from={get_last_timestamp()}&to={today}&sortBy=popularity&apiKey={news_api_key}"

    response_news = requests.get(news_url)
    # print(response_news.content)
    if response_news.status_code == 200:
        news_data = response_news.json()

    else:
        remaining_quota = response_news.headers.get("X-RateLimit-Remaining")
        print(f"Remaining quota: {response_news.content}")
        news_data = "No news data available"

    articles = news_data.get("articles", [])

    news_summary = "\n".join(
        [f"- {article['title']}: {article['description']}" for article in articles]
    )

    read_df = pd.DataFrame(articles)
    if read_df.empty:
        return

    if not os.path.exists("articles.csv"):
        df_expanded = pd.json_normalize(read_df["source"])
        df = read_df.assign(
            id=df_expanded["id"], name=df_expanded["name"], search_date=today
        ).drop(columns=["source"])
    else:
        df = pd.read_csv("articles.csv")
        df_expanded = pd.json_normalize(read_df["source"])
        read_df = read_df.assign(
            id=df_expanded["id"], name=df_expanded["name"], search_date=today
        ).drop(columns=["source"])
        df = pd.concat([df, read_df])

    df.to_csv("articles.csv", index=False)
    save_timestamp()
    print(df[["title", "description", "publishedAt"]])
    return news_summary


if __name__ == "__main__":
    print(get_news_summary())
