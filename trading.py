## TODO
# 코드 완성해서 실행까지 시켜보기 누락된 부분들 추가하기

import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from sqlite3.dbapi2 import Connection

import openai
import pandas as pd
import pyupbit
import requests
import ta
from dotenv import load_dotenv
from openai import OpenAI
from ta.utils import dropna

import prompt
from news_factory_excute import fetch_and_save_news

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# # 4. Execute trade decision using Upbit API
access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")
upbit = pyupbit.Upbit(access, secret)


def init_db():
    conn = sqlite3.connect("bitcoin_trades.db")
    c = conn.cursor()
    c.execute("""
              CREATE TABLE IF NOT EXISTS trades
              (id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT,
              decision TEXT,
              percentage INTEGER,
              reason TEXT,
              btc_balance REAL,
              krw_balance REAL,
              btc_avg_buy_price REAL,
              btc_krw_price REAL,
              reflection TEXT)
              """)
    conn.commit()
    return conn


def log_trade(
    conn: Connection,
    decision,
    percentage,
    reason,
    btc_balance,
    krw_balance,
    btc_avg_buy_price,
    btc_krw_price,
    reflection,
):
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute(
        """
            INSERT INTO trades
            (timestamp, decision, percentage, reason, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price, reflection)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            timestamp,
            decision,
            percentage,
            reason,
            btc_balance,
            krw_balance,
            btc_avg_buy_price,
            btc_krw_price,
            reflection,
        ),
    )
    conn.commit()


def get_recent_trades(conn: Connection, days=7):
    c = conn.cursor()
    days_ago = (datetime.now() - timedelta(days=days)).isoformat()
    print(days_ago)

    c.execute(
        "SELECT * FROM trades WHERE timestamp > ? ORDER BY timestamp DESC", (days_ago,)
    )

    columns = [column[0] for column in c.description]
    return pd.DataFrame.from_records(data=c.fetchall(), columns=columns)


def get_fear_and_greed_index():
    url = "https://api.alternative.me/fng/"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        data: dict = data["data"][0]
        data["timestamp"] = datetime.fromtimestamp(float(data["timestamp"])).strftime(
            "%Y%m%d%H"
        )
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Fear and Greed Index: {e}")
        return None


def add_indicators(df: pd.DataFrame):
    # 볼린저 밴드 (20일 윈도우)
    df["bb_bbm"] = ta.volatility.BollingerBands(
        close=df["close"], window=20, window_dev=2
    ).bollinger_mavg()
    df["bb_bbh"] = ta.volatility.BollingerBands(
        close=df["close"], window=20, window_dev=2
    ).bollinger_hband()
    df["bb_bbl"] = ta.volatility.BollingerBands(
        close=df["close"], window=20, window_dev=2
    ).bollinger_lband()

    # RSI (14일 윈도우)
    df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()

    # MACD (기본 설정 12, 26, 9)
    macd = ta.trend.MACD(
        close=df["close"], window_slow=26, window_fast=12, window_sign=9
    )
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_diff"] = macd.macd_diff()

    # 단순 이동 평균 (20일)
    df["sma_20"] = ta.trend.SMAIndicator(close=df["close"], window=20).sma_indicator()

    # 지수 이동 평균 (12일)
    df["ema_12"] = ta.trend.EMAIndicator(close=df["close"], window=12).ema_indicator()

    # Stochastic Oscillator (14일)
    stoch = ta.momentum.StochasticOscillator(
        high=df["high"], low=df["low"], close=df["close"], window=14, smooth_window=3
    )
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()

    # Average True Range (ATR) (14일)
    df["atr"] = ta.volatility.AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=14
    ).average_true_range()

    # On-Balance Volume (OBV)
    df["obv"] = ta.volume.OnBalanceVolumeIndicator(
        close=df["close"], volume=df["volume"]
    ).on_balance_volume()

    # df = df.fillna(df.mean())

    return df


def parser_ai_response(response_json_text):
    try:
        json_match = re.search(r"\{.*?\}", response_json_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed_json = json.loads(json_str)
            decision = parsed_json.get("decision").upper()
            percentage = parsed_json.get("percentage")
            reason = parsed_json.get("reason")
            return {"decision": decision, "percentage": percentage, "reason": reason}
        else:
            logger.error("No JSON found in AI response.")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return None


def calculate_performance(trades_df: pd.DataFrame):
    if trades_df.empty:
        return 0
    initial_balance = trades_df.iloc[-1]["krw_balance"] + trades_df.iloc[-1][
        "btc_balance"
    ] * pyupbit.get_current_price("KRW-BTC")

    final_balance = trades_df.iloc[0]["krw_balance"] + trades_df.iloc[0][
        "btc_balance"
    ] * pyupbit.get_current_price("KRW-BTC")

    print(initial_balance, final_balance)
    print(trades_df.iloc[0]["krw_balance"], trades_df.iloc[0]["btc_balance"])
    print(trades_df.iloc[-1]["krw_balance"], trades_df.iloc[-1]["btc_balance"])

    return (final_balance - initial_balance) / initial_balance * 100


def excute_trade(decision, percentage):
    print("siy", decision)
    if decision == "BUY":
        my_krw = upbit.get_balance("KRW")
        if my_krw is None:
            logger.error("Failed to retrieve KRW balance.")
            return

        buy_amount = my_krw * (percentage / 100) * 0.9995  # 고려된 수수료
        if buy_amount > 5000:
            logger.info(f"Buy Order Executed: {percentage}% of available KRW")
            try:
                order = upbit.buy_market_order("KRW-BTC", buy_amount)
                if order:
                    logger.info(f"Buy order executed successfully: {order}")
                    order_executed = True
                else:
                    logger.error("Buy order failed.")
            except Exception as e:
                logger.error(f"Error executing buy order: {e}")
        else:
            logger.warning("Buy Order Failed: Insufficient KRW (less than 5000 KRW)")

    elif decision == "SELL":
        my_btc = upbit.get_balance("KRW-BTC")
        if my_btc is None:
            logger.error("Failed to retrieve BTC balance.")
            return

        sell_amount = my_btc * (percentage / 100)
        current_price = pyupbit.get_current_price("KRW-BTC")
        if sell_amount * current_price > 5000:
            logger.info(f"Sell Order Executed: {percentage}% of held BTC")
            try:
                order = upbit.sell_market_order("KRW-BTC", sell_amount)
                if order:
                    logger.info(f"Sell order executed successfully: {order}")
                    order_executed = True
                else:
                    logger.error("Sell order failed.")
            except Exception as e:
                logger.error(f"Error executing sell order: {e}")
        else:
            logger.warning(
                "Sell Order Failed: Insufficient BTC (less than 5000 KRW worth)"
            )
    elif decision == "HOLD":
        logger.info("Decision is to hold. No action taken.")
        order_executed = True
    else:
        logger.error("Invalid decision received from AI")
        return order_executed

    return order_executed


def get_reflection_from_db(conn: Connection):
    c = conn.cursor()

    c.execute("SELECT reflection FROM trades ORDER BY ROWID DESC LIMIT 1")

    return c.fetchone()


def get_reflection(trades_df, current_market_data):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "You are an AI trading"},
            {
                "role": "user",
                "content": f"""
                Recent trading data:
                {trades_df.to_json(orient='records')}

                Current market data:
                {current_market_data}

                Overall performance in the last 7 days: {calculate_performance(trades_df):.2f}%

                Please analyze this data and provide:
                1. A brief reflection on the recent trading decisions
                2. Insights on what worked well and what didn't
                3. Suggestions for improvement in future trading decisions
                4. Any patterns or trends you notice in the market data

                Limit your response to 250 words or less.
                """,
            },
        ],
    )

    try:
        response_content = response.choices[0].message.content
        return response_content
    except (IndexError, AttributeError) as e:
        logger.error(f"Error extracting response content: {e}")
        return None


def ai_trading():
    global upbit

    all_balances = upbit.get_balances()

    filtered_balances = [
        balance for balance in all_balances if balance["currency"] in ["BTC", "KRW"]
    ]

    orderbook = pyupbit.get_orderbook("KRW-BTC")

    df_daily: pd.DataFrame = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=30)
    df_daily = dropna(df_daily)

    df_daily.index = df_daily.index.strftime("%Y%m%d")
    df_daily = add_indicators(df_daily)

    df_hourly: pd.DataFrame = pyupbit.get_ohlcv(
        "KRW-BTC", interval="minute60", count=24
    )
    # df_daily.index = pd.to_datetime(df_daily.index // 1000, unit="s")
    df_hourly.index = df_hourly.index.strftime("%Y%m%d%H")

    df_hourly = add_indicators(df_hourly)

    fear_greed_index = get_fear_and_greed_index()

    # serpapi.com
    news_headlines = fetch_and_save_news()

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if not client.api_key:
        logger.error("OpenAI API key is missing or invalid.")

    try:
        with sqlite3.connect("bitcoin_trades.db") as conn:
            recent_trades = get_recent_trades(conn)

            current_market_date = {
                "feer_greed_index": fear_greed_index,
                "news_headlines": news_headlines,
                "orderbook": orderbook,
                "daily_ohlcv": df_daily.to_dict(),
                "hourly_ohlcv": df_hourly.to_dict(),
            }

            # reflection = get_reflection(recent_trades, current_market_date)
            reflection = ""

            print(prompt.get_system_prompt("reflection"))
            print(
                prompt.get_user_prompt(
                    df_daily,
                    df_hourly,
                    filtered_balances,
                    orderbook,
                    news_headlines,
                    fear_greed_index,
                )
            )

            # response = client.chat.completions.create(
            #     model="gpt-4o",
            #     messages=[
            #         {
            #             "role": "user",
            #             "content": (prompt.get_system_prompt(reflection)),
            #         },
            #         {
            #             "role": "user",
            #             "content": [
            #                 {
            #                     "type": "text",
            #                     "text": prompt.get_user_prompt(
            #                         df_daily,
            #                         df_hourly,
            #                         filtered_balances,
            #                         orderbook,
            #                         news_headlines,
            #                         fear_greed_index,
            #                     ),
            #                 }
            #             ],
            #         },
            #     ],
            # )

            # response_text = response.choices[0].message.content

            # parsed_response = parser_ai_response(response_text)

            parsed_response = {"decision": "HOLD", "percentage": 0, "reason": "test"}

            decision = parsed_response.get("decision")
            percentage = parsed_response.get("percentage")
            reason = parsed_response.get("reason")

            logger.info(f"AI Decision: {decision.upper()}")
            logger.info(f"percentage: {percentage}")
            logger.info(f"Decision reason: {reason}")

            order_excuted = False

            result = excute_trade(decision=decision, percentage=percentage)

            time.sleep(2)
            balances = upbit.get_balances()
            print(type(balances), balances)
            btc_balance = next(
                (
                    float(balance["balance"])
                    for balance in balances
                    if balance["currency"] == "BTC"
                ),
                0,
            )
            krw_balance = next(
                (
                    float(balance["balance"])
                    for balance in balances
                    if balance["currency"] == "KRW"
                ),
                0,
            )
            btc_avg_buy_price = next(
                (
                    float(balance["avg_buy_price"])
                    for balance in balances
                    if balance["currency"] == "BTC"
                ),
                0,
            )

            print(btc_balance)

            current_btc_price = pyupbit.get_current_price("KRW-BTC")
            print(current_btc_price)

            log_trade(
                conn,
                decision,
                percentage if order_excuted else 0,
                reason,
                btc_balance,
                krw_balance,
                btc_avg_buy_price,
                current_btc_price,
                reflection,
            )

    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        return


if __name__ == "__main__":
    init_db()
    load_dotenv()

    trading_in_progress = False

    def job():
        global trading_in_progress
        if trading_in_progress:
            logger.warning("Trading job is already in progress, skipping this run")
            return

        try:
            trading_in_progress = True
            ai_trading()
        except Exception as e:
            logger.error(f"An error occurred: {e}")
        finally:
            trading_in_progress = False

    job()

    # schedule.every().day.at("03:00").do(job)
    # schedule.every().day.at("09:00").do(job)
    # schedule.every().day.at("15:00").do(job)
    # schedule.every().day.at("21:00").do(job)

    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)
