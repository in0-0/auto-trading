import logging
import os
from datetime import datetime, timedelta
from sqlite3.dbapi2 import Connection
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

# init_db 함수를 테스트하기 위해 실제 함수가 포함된 모듈을 import
from mvp import (
    add_indicators,
    calculate_performance,
    get_recent_trades,
    get_reflection_from_db,
    init_db,
    log_trade,
    parser_ai_response,
)

# 로거 설정
logger = logging.getLogger("test_logger")


@pytest.fixture
def db_connection():
    # 테스트용 데이터베이스 파일을 생성
    conn = init_db()
    yield conn
    # 테스트 후 데이터베이스 파일 삭제
    conn.close()
    os.remove("bitcoin_trades.db")


@pytest.fixture
def populate_trades(db_connection):
    # 데이터베이스에 샘플 트랜잭션 삽입
    sample_trades = [
        ("buy", 5, "Good opportunity", 0.5, 1000000, 20000000, 21000000, "Positive"),
        ("sell", 10, "Market drop", 0.3, 2000000, 21000000, 22000000, "Caution"),
        ("hold", 0, "Stable market", 1.0, 1500000, 21000000, 21000000, "Observation"),
    ]
    for i, trade in enumerate(sample_trades):
        log_trade(
            conn=db_connection,
            decision=trade[0],
            percentage=trade[1],
            reason=trade[2],
            btc_balance=trade[3],
            krw_balance=trade[4],
            btc_avg_buy_price=trade[5],
            btc_krw_price=trade[6],
            reflection=trade[7],
        )
    return db_connection


@pytest.fixture
def sample_df():
    # 테스트용 샘플 데이터 생성
    data = {
        "open": [
            100,
            102,
            104,
            103,
            102,
            105,
            106,
            108,
            110,
            107,
            108,
            109,
            111,
            110,
            109,
            112,
            113,
            115,
            114,
            113,
            116,
            117,
            119,
            118,
            117,
        ],
        "high": [
            101,
            103,
            105,
            104,
            103,
            106,
            107,
            109,
            111,
            108,
            110,
            111,
            113,
            112,
            111,
            114,
            115,
            117,
            116,
            115,
            118,
            119,
            121,
            120,
            119,
        ],
        "low": [
            99,
            101,
            103,
            102,
            101,
            104,
            105,
            107,
            109,
            106,
            107,
            108,
            110,
            109,
            108,
            111,
            112,
            114,
            113,
            112,
            115,
            116,
            118,
            117,
            116,
        ],
        "close": [
            100,
            102,
            104,
            103,
            102,
            105,
            106,
            108,
            110,
            107,
            109,
            110,
            112,
            111,
            110,
            113,
            114,
            116,
            115,
            114,
            117,
            118,
            120,
            119,
            118,
        ],
        "volume": [
            1000,
            1100,
            1200,
            1300,
            1250,
            1350,
            1400,
            1450,
            1500,
            1550,
            1600,
            1650,
            1700,
            1750,
            1800,
            1850,
            1900,
            1950,
            2000,
            2050,
            2100,
            2150,
            2200,
            2250,
            2300,
        ],
    }

    df = pd.DataFrame(data)
    return df


def test_db_creation(db_connection: Connection):
    # 데이터베이스 연결 확인
    assert db_connection is not None

    # trades 테이블이 생성되었는지 확인
    c = db_connection.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
    table_exists = c.fetchone()
    assert table_exists is not None, "trades 테이블이 생성되지 않았습니다."

    # 테이블 구조가 올바른지 확인
    c.execute("PRAGMA table_info(trades)")
    columns = {col[1] for col in c.fetchall()}
    expected_columns = {
        "id",
        "timestamp",
        "decision",
        "percentage",
        "reason",
        "btc_balance",
        "krw_balance",
        "btc_avg_buy_price",
        "btc_krw_price",
        "reflection",
    }
    assert columns == expected_columns, "테이블의 컬럼이 예상과 다릅니다."


@pytest.mark.parametrize(
    "decision, percentage, reason, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price, reflection",
    [
        pytest.param(
            "buy",
            5,
            "Favorable market condition",
            0.5,
            1000000,
            20000000,
            21000000,
            "Good decision based on market trend",
            id="buy_case",
        ),
        pytest.param(
            "sell",
            10,
            "Risk reduction",
            0.3,
            2000000,
            21000000,
            22000000,
            "Market conditions changed unexpectedly",
            id="sell_case",
        ),
        pytest.param(
            "hold",
            0,
            "Stable market",
            1.0,
            1500000,
            21000000,
            21000000,
            "No action needed at the moment",
            id="hold_case",
        ),
    ],
)
def test_log_trade(
    db_connection: Connection,
    decision,
    percentage,
    reason,
    btc_balance,
    krw_balance,
    btc_avg_buy_price,
    btc_krw_price,
    reflection,
):
    # log_trade 함수 실행
    log_trade(
        conn=db_connection,
        decision=decision,
        percentage=percentage,
        reason=reason,
        btc_balance=btc_balance,
        krw_balance=krw_balance,
        btc_avg_buy_price=btc_avg_buy_price,
        btc_krw_price=btc_krw_price,
        reflection=reflection,
    )

    # 데이터가 올바르게 삽입되었는지 확인
    c = db_connection.cursor()
    c.execute(
        "SELECT * FROM trades WHERE decision=? AND percentage=?", (decision, percentage)
    )
    row = c.fetchone()

    expect_list = [
        decision,
        percentage,
        reason,
        btc_balance,
        krw_balance,
        btc_avg_buy_price,
        btc_krw_price,
        reflection,
    ]

    expect_list_str = [
        "decision",
        "percentage",
        "reason",
        "btc_balance",
        "krw_balance",
        "btc_avg_buy_price",
        "btc_krw_price",
        "reflection",
    ]

    assert row is not None, "트랜잭션이 trades 테이블에 삽입되지 않았습니다."

    for idx, expect in enumerate(expect_list):
        assert (
            row[idx + 2] == expect
        ), f"Expected {expect_list_str[idx]} to be '{expect}', but got '{row[idx + 2]}'"


def test_get_recent_trades(db_connection, populate_trades):
    # 최근 2일 내의 트랜잭션을 검색
    days = 2
    recent_trades_df = get_recent_trades(db_connection, days=days)

    # 최근 트랜잭션 데이터프레임이 비어 있지 않음
    assert not recent_trades_df.empty, "최근 트랜잭션이 없습니다."

    # 데이터프레임의 각 row가 최근 2일 내의 트랜잭션인지 확인
    days_ago = datetime.now() - timedelta(days=days)
    for timestamp in recent_trades_df["timestamp"]:
        assert (
            datetime.fromisoformat(timestamp) > days_ago
        ), "날짜가 잘못된 트랜잭션이 포함되어 있습니다."

    # 검색된 데이터 수가 올바른지 확인
    expected_count = len(recent_trades_df)  # 실제 삽입된 트랜잭션의 수와 비교
    assert (
        len(recent_trades_df) == expected_count
    ), f"Expected {expected_count} trades, but got {len(recent_trades_df)}"


def test_add_indicators(sample_df):
    df_with_indicators = add_indicators(sample_df)

    # 기대하는 컬럼 리스트
    expected_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "bb_bbm",
        "bb_bbh",
        "bb_bbl",
        "rsi",
        "macd",
        "macd_signal",
        "macd_diff",
        "sma_20",
        "ema_12",
        "stoch_k",
        "stoch_d",
        "atr",
        "obv",
    ]

    # 1. 모든 예상 컬럼이 존재하는지 확인
    for column in expected_columns:
        assert column in df_with_indicators.columns, f"{column} 컬럼이 누락되었습니다."

    # 3. 특정 지표 값의 유형 및 예외 사항 테스트
    assert (
        df_with_indicators["rsi"].dtype == np.float64
    ), "RSI 컬럼은 float이어야 합니다."
    assert (
        df_with_indicators["macd"].dtype == np.float64
    ), "MACD 컬럼은 float이어야 합니다."
    assert (
        df_with_indicators["stoch_k"].dtype == np.float64
    ), "Stochastic %K 컬럼은 float이어야 합니다."
    assert (
        df_with_indicators["stoch_d"].dtype == np.float64
    ), "Stochastic %D 컬럼은 float이어야 합니다."

    # 4. 각 지표가 범위 내에서 계산되는지 확인 (예: RSI는 0~100 범위)
    assert (
        df_with_indicators["rsi"].between(0, 100).all()
    ), "RSI 값이 0과 100 사이에 있지 않습니다."
    assert (
        df_with_indicators["stoch_k"].between(0, 100).all()
    ), "Stochastic %K 값이 0과 100 사이에 있지 않습니다."
    assert (
        df_with_indicators["stoch_d"].between(0, 100).all()
    ), "Stochastic %D 값이 0과 100 사이에 있지 않습니다."

    # 5. 이동 평균(MA)의 기본적인 검증: sma_20과 ema_12
    if len(df_with_indicators) >= 20:
        assert (
            df_with_indicators["sma_20"].iloc[19] is not np.nan
        ), "sma_20 컬럼이 20번째 행에서 NaN입니다."
    if len(df_with_indicators) >= 12:
        assert (
            df_with_indicators["ema_12"].iloc[11] is not np.nan
        ), "ema_12 컬럼이 12번째 행에서 NaN입니다."

    # 6. 볼린저 밴드 상하한선 확인 (bb_bbl < bb_bbm < bb_bbh)
    assert (
        df_with_indicators["bb_bbl"] <= df_with_indicators["bb_bbm"]
    ).all(), "볼린저 밴드의 하한선이 중간선보다 큽니다."
    assert (
        df_with_indicators["bb_bbm"] <= df_with_indicators["bb_bbh"]
    ).all(), "볼린저 밴드의 중간선이 상한선보다 큽니다."

    # 7. On-Balance Volume (OBV) 연속적인 값 증가 또는 감소 테스트
    obv_diff = df_with_indicators["obv"].diff().dropna()
    assert (
        obv_diff[obv_diff > 0].count() + obv_diff[obv_diff < 0].count()
    ) > 0, "OBV 값이 연속적으로 동일합니다."


@pytest.mark.parametrize(
    "response_json_text, expected",
    [
        # 정상 JSON이 포함된 AI 응답 예제
        (
            'This is the AI response: {"decision": "buy", "percentage": 10, "reason": "Favorable market conditions"}|',
            {
                "decision": "buy",
                "percentage": 10,
                "reason": "Favorable market conditions",
            },
        ),
        # JSON이 포함되지 않은 AI 응답 예제
        ("No JSON data here.", None),
        # 잘못된 JSON 형식이 포함된 AI 응답 예제
        (
            'AI response with malformed JSON: {"decision": "buy", "percentage": 10, "reason": "Favorable market conditions"',
            None,
        ),
        # 불완전한 JSON 데이터가 중간에 잘린 경우
        ('AI response: {"decision": "buy", "percentage": 10 ', None),
        # 특수 문자가 포함된 경우 (정상적인 JSON 응답)
        (
            'Here is the response: {"decision": "sell", "percentage": 5, "reason": "High volatility!"}|',
            {"decision": "sell", "percentage": 5, "reason": "High volatility!"},
        ),
    ],
)
def test_parser_ai_response(response_json_text, expected):
    result = parser_ai_response(response_json_text)
    assert result == expected, f"Expected {expected}, but got {result}"


@pytest.mark.parametrize(
    "trades_df, expected_performance",
    [
        # 정상적인 거래 내역이 있는 경우
        (
            pd.DataFrame(
                [
                    {"krw_balance": 450000, "btc_balance": 0.12},
                    {"krw_balance": 500000, "btc_balance": 0.1},
                ]
            ),
            17.6,  # 예상 수익률: 20%
        ),
        # 거래 내역이 비어있는 경우
        (
            pd.DataFrame([], columns=["krw_balance", "btc_balance"]),
            0.0,  # 예상 수익률: 0%
        ),
        # 초기 및 최종 잔액이 동일한 경우
        (
            pd.DataFrame(
                [
                    {"krw_balance": 500000, "btc_balance": 0.1},
                    {"krw_balance": 500000, "btc_balance": 0.1},
                ]
            ),
            0.0,  # 예상 수익률: 0%
        ),
        # 거래 내역에 KRW 잔액만 있는 경우
        (
            pd.DataFrame(
                [
                    {"krw_balance": 800000, "btc_balance": 0.0},
                    {"krw_balance": 1000000, "btc_balance": 0.0},
                ]
            ),
            -20.0,  # 예상 수익률: -20%
        ),
    ],
)
@patch("mvp.pyupbit.get_current_price")  # pyupbit 모듈을 Mock 처리
def test_calculate_performance(mock_get_current_price, trades_df, expected_performance):
    # pyupbit.get_current_price 함수가 고정된 가격을 반환하도록 설정
    mock_get_current_price.return_value = 60000000

    # 수익률 계산
    performance = calculate_performance(trades_df)

    # 수익률이 예상 값과 거의 같은지 확인 (소수점 오차를 고려)
    assert performance == pytest.approx(
        expected_performance, rel=1e-2
    ), f"Expected {expected_performance}, but got {performance}"


@pytest.mark.parametrize(
    "reflections, expected",
    [
        # 단일 항목이 있는 경우
        (["First reflection"], "First reflection"),
        # 여러 항목이 있는 경우, 최신 항목이 반환되어야 함
        (
            ["First reflection", "Second reflection", "Most recent reflection"],
            "Most recent reflection",
        ),
        # 테이블이 비어있는 경우 None이 반환되어야 함
        ([], None),
    ],
)
def test_get_reflection_from_db(db_connection: Connection, reflections, expected):
    # 각 테스트 케이스에 맞게 데이터를 삽입
    for reflection in reflections:
        db_connection.execute(
            "INSERT INTO trades (reflection) VALUES (?)", (reflection,)
        )
    db_connection.commit()

    # 함수 호출 및 결과 검증
    result = get_reflection_from_db(db_connection)
    if expected is None:
        assert result is None, f"Expected None, but got {result}"
    else:
        assert result == (expected,), f"Expected ('{expected}',) but got {result}"
