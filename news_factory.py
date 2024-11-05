import os
from typing import Dict, List

from newsapi import NewsApiClient
from serpapi import GoogleSearch


class NewsAPIClient:
    """Client for NewsAPI using the official Python SDK."""

    def __init__(self):
        self.client = NewsApiClient(api_key=os.getenv("NEWS_API_KEY"))
        self.quota_exceeded = False

    def request_top_headlines(self, params: Dict) -> List[Dict]:
        """Fetch top headlines from NewsAPI and standardize response."""
        from_date = params.pop("from", None)
        to_date = params.pop("to", None)
        try:
            response = self.client.get_everything(
                q=params.get("q"),
                from_param=from_date,
                to=to_date,
                language=params.get("language", "en"),
                sort_by=params.get("sortBy", "popularity"),
            )
            return [
                {
                    "title": article["title"],
                    "description": article["description"],
                    "url": article["url"],
                    "publishedAt": article["publishedAt"],
                    "source": article["source"]["name"],
                }
                for article in response.get("articles", [])
            ]
        except Exception as e:
            self.quota_exceeded = True
            print(f"NewsAPI error: {e}")
            return


class SerpAPIClient:
    """Client for SerpAPI using the official Python SDK."""

    def __init__(self):
        self.api_key = os.getenv("SERP_API_KEY")
        self.quota_exceeded = False

    def request_top_headlines(self, params: Dict) -> List[Dict]:
        """Fetch top headlines from SerpAPI and standardize response."""
        print(self.api_key)
        search_params = {
            "engine": "google",
            "q": params.get("q"),
            "tbm": "nws",  # news search type for SerpAPI
            "serp_api_key": self.api_key,
            "hl": params.get("language", "en"),
            "tbs": "qdr:w",
        }
        try:
            search = GoogleSearch(search_params)
            response = search.get_dict()
            return [
                {
                    "title": result["title"],
                    "description": result.get("snippet"),
                    "url": result.get("link"),
                    "publishedAt": result.get("date"),
                    "source": result.get("source"),
                }
                for result in response.get("news_results", [])
            ]
        except Exception as e:
            self.quota_exceeded = True
            print(f"SerpAPI error: {e}")
            return


class NewsApiFactory:
    """Factory for creating the appropriate API client based on quota availability."""

    def __init__(self):
        self.clients = [NewsAPIClient(), SerpAPIClient()]
        self.current_client_index = 0

    def _switch_to_next_available_client(self):
        """Switch to the next available client with quota remaining."""
        for _ in range(len(self.clients)):
            self.current_client_index = (self.current_client_index + 1) % len(
                self.clients
            )
            if not self.clients[self.current_client_index].quota_exceeded:
                return
        raise Exception("All API quotas are exhausted. Please try again later.")

    def request_top_headlines(self, params: Dict) -> List[Dict]:
        """
        Fetch top headlines using the current client.
        If quota is exceeded, switch to the next available client.
        """
        for _ in range(len(self.clients)):
            current_client = self.clients[self.current_client_index]
            try:
                response = current_client.request_top_headlines(params)
                if response:
                    return response
            except Exception as e:
                print(f"Error with {current_client.__class__.__name__}: {e}")
            # Switch to the next client if the current one fails
            self._switch_to_next_available_client()

        raise Exception("Unable to fetch news from any available clients.")
