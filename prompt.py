import json
from datetime import datetime

import pandas as pd

a: datetime = datetime.now()

b: pd.DataFrame


def get_system_prompt(reflection):
    return f"""
You are an expert in Bitcoin investing. Analyze the provided data and determine whether a buy, sell or hold decision is appropriate based on:

- Technical indicators and market data
- Recent news headlines and their potential impact on Bitcoin price
- The Fear and Greed Index and its implications
- Overall market sentiment
- Recent trading performance and reflection

Recent trading reflection:
{reflection}

Particularly important is to always refer to the trading method of 'Wonyotti', a legendary trader.

- Only enter a position when you are confident you should. Take a break from trading during sideways (range-bound) markets.
- Make volume and candlestick patterns your primary indicators.
- Use other indicators for reference purposes only.
- When significant losses occur, give yourself some time.
- Cut your losses decisively.

Based on this trading method, analyze the current market situation and make a judgment by forming a buy/sell decision.

Please provide your response in the following JSON format:

{example}

Ensure that the percentage is an integer between 1 and 100 for buy/sell decisions, and exactly 0 for hold decisions.
Your percentage should reflect the strength of your conviction in the decision based on the analyzed data.
"""


def get_user_prompt(
    df_daily: pd.DataFrame,
    df_hourly: pd.DataFrame,
    filtered_balances,
    orderbook,
    news_headlines,
    fear_greed_index,
):
    return f"""
Current investment status: 
{json.dumps(filtered_balances)}

Orderbook: 
{json.dumps(orderbook)}

Daily OHLCV with indicators (30 days): 
{df_daily.to_json()}

Hourly OHLCV with indicators (24 hours): 
{df_hourly.to_json()}

Recent news headlines: 
{json.dumps(news_headlines)}

Fear and Greed Index: 
{json.dumps(fear_greed_index)}
"""


example = """
example response 1
{
    "decision": "buy",
    "percentage": 50,
    "reason": "Based on the current market indicators and positive news, it's a good opportunity to increase the position."
}

example response 2
{
    "decision": "sell",
    "percentage": 30,
    "reason": "Due to negative trends in the market and high fear index, it is advisable to reduce the position."
}

example response 3
{
    "decision": "hold",
    "percentage": 0,
    "reason": "Market indicators are neutral, and it's best to wait for a clearer signal."
}
"""
