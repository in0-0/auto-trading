# 2. Fetch Bitcoin-related news using a news API
import os
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

"""
1020 : 뉴스 api 정상동작 하는 것 확인, csv로 저장할 수 있는 것 확인.

# TODO
- 직전 타임스템프 이후로 기사 파싱 할 수 있도록 변경한 후 기사 내용에 대한 확인 로직 추가

"""
today = datetime.now()
today_str = today.isoformat(timespec="seconds")
print(today)
timestamp = "timestamp.txt"


def get_last_timestamp():
    if os.path.exists(timestamp):
        with open(timestamp, "r") as f:
            timestamp_str = f.read().strip()
            return datetime.fromisoformat(timestamp_str)
    return None


# 타임스탬프 저장
def save_timestamp(timestamp):
    with open(timestamp, "w") as f:
        f.write(timestamp.isoformat())


def main():
    news_api_key = os.getenv("NEWS_API_KEY")
    news_query = "bitcoin"
    news_url = f"https://newsapi.org/v2/everything?q={news_query}&from=2024-10-15T14:05:39&to={today}&sortBy=popularity&apiKey={news_api_key}"

    response_news = requests.get(news_url)
    print(response_news.content)
    if response_news.status_code == 200:
        news_data = response_news.json()

    else:
        news_summary = "No news data available"

    articles = news_data.get("articles", [])

    news_summary = "\n".join(
        [f"- {article['title']}: {article['description']}" for article in articles[:1]]
    )

    if not os.path.exists("articles.csv"):
        df = pd.DataFrame(articles)
        df_expanded = pd.json_normalize(df["source"])
        df = df.assign(
            id=df_expanded["id"], name=df_expanded["name"], search_date=today
        ).drop(columns=["source"])
    else:
        df = pd.read_csv("articles.csv")
        tmp_df = pd.DataFrame(articles)
        df_expanded = pd.json_normalize(tmp_df["source"])
        tmp_df = tmp_df.assign(
            id=df_expanded["id"], name=df_expanded["name"], search_date=today
        ).drop(columns=["source"])
        df = pd.concat([df, tmp_df])

    print(df)
    df.to_csv("articles.csv", index=False)
    return news_summary


if __name__ == "__main__":
    print(main())
