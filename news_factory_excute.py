import os
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

from news_factory import (
    NewsApiFactory,  # Assume we have implemented NewsApiFactory as provided
)

# Load environment variables
load_dotenv()

# Define timestamp file path and current date
timestamp_file = "timestamp.txt"
today = datetime.now()
today_str = today.isoformat(timespec="seconds")


def get_last_timestamp():
    """Retrieve the last timestamp from the file or set default to current time."""
    if os.path.exists(timestamp_file):
        with open(timestamp_file, "r") as f:
            timestamp_str = f.read().strip()
            last_date = datetime.fromisoformat(timestamp_str)
            from_data = (last_date - timedelta(days=1)).isoformat(timespec="seconds")
            return from_data
    return today_str


def save_timestamp():
    """Save the current timestamp to the timestamp file."""
    with open(timestamp_file, "w") as f:
        f.write(today_str)


def fetch_and_save_news():
    factory = NewsApiFactory()
    """Fetch news using the NewsApiFactory and save it to a CSV file."""
    # Prepare parameters for API request
    params = {
        "q": "bitcoin",
        "from": get_last_timestamp(),
        "to": today_str,
        "sortBy": "popularity",
        "language": "en",
    }

    # Fetch news using factory
    news_data = factory.request_top_headlines(params)

    # Save articles to CSV
    news_summary = "\n".join(
        [f"{idx}. {article['title']}" for idx, article in enumerate(news_data)]
    )
    read_df = pd.DataFrame(news_data)

    read_df.to_csv("articles.csv", index=False)
    save_timestamp()
    return news_summary


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()

    # Initialize the factory with API keys
    newsapi_key = os.getenv("NEWS_API_KEY")
    serpapi_key = os.getenv("SERP_API_KEY")
    factory = NewsApiFactory(newsapi_key=newsapi_key, serpapi_key=serpapi_key)

    # Fetch and print news summary
    print(fetch_and_save_news(factory))
