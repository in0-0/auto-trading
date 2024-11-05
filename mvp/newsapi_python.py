import os

from dotenv import load_dotenv
from newsapi import NewsApiClient

# Init

load_dotenv()
news_api_key = os.getenv("NEWS_API_KEY")
newsapi = NewsApiClient(api_key=news_api_key)

# /v2/top-headlines
top_headlines = newsapi.get_top_headlines(
    q="bitcoin",
    sources="bbc-news,the-verge",
    # category="business",
    language="en",
    # country="us",
)

# /v2/everything
all_articles = newsapi.get_everything(
    q="bitcoin",
    sources="bbc-news,the-verge",
    domains="bbc.co.uk,techcrunch.com",
    from_param="2024-10-11",
    to="2024-10-28",
    language="en",
    sort_by="relevancy",
    page=1,
)

# /v2/top-headlines/sources
sources = newsapi.get_sources()

print(all_articles)
