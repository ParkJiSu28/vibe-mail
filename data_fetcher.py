import os
import datetime
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
load_dotenv()

# pykrx 임포트 전 KRX 자격증명 주입 (매 실행시 재로그인)
os.environ.setdefault("KRX_ID", os.getenv("KRX_ID", ""))
os.environ.setdefault("KRX_PW", os.getenv("KRX_PW", ""))

import pandas as pd
from pykrx import stock
import yfinance as yf

logger = logging.getLogger(__name__)


def _get_prev_trading_day() -> str:
    """가장 최근 거래일 (YYYYMMDD) 반환 - pykrx holiday 자동 처리 활용"""
    today = datetime.date.today()
    for i in range(1, 10):
        d = (today - datetime.timedelta(days=i)).strftime("%Y%m%d")
        try:
            df = stock.get_market_ohlcv_by_ticker(d, market="KOSPI")
            # 거래대금이 있는 종목이 100개 이상이면 정상 거래일
            if not df.empty and (df["거래대금"] > 0).sum() > 100:
                return d
        except Exception:
            continue
    raise RuntimeError("최근 거래일 조회 실패")


def _fetch_all_ohlcv(date_str: str) -> pd.DataFrame:
    """KOSPI + KOSDAQ 전 종목 OHLCV 합산"""
    frames = []
    for market in ("KOSPI", "KOSDAQ"):
        try:
            df = stock.get_market_ohlcv_by_ticker(date_str, market=market)
            if not df.empty:
                frames.append(df)
        except Exception as e:
            logger.warning(f"{market} OHLCV 실패 ({date_str}): {e}")
    return pd.concat(frames) if frames else pd.DataFrame()


def get_top30_stocks() -> tuple[pd.DataFrame, str]:
    """전 거래일 거래대금 상위 30 종목 DataFrame과 날짜문자열 반환"""
    date_str = _get_prev_trading_day()
    logger.info(f"기준 거래일: {date_str}")

    df_all = _fetch_all_ohlcv(date_str)
    if df_all.empty:
        raise RuntimeError(f"{date_str} 데이터 없음")

    # 거래대금 > 0 필터 후 상위 30
    df_active = df_all[df_all["거래대금"] > 0].copy()
    top30 = df_active.nlargest(30, "거래대금").copy()

    # 종목명 추가
    names = []
    for ticker in top30.index:
        try:
            names.append(stock.get_market_ticker_name(ticker))
        except Exception:
            names.append(ticker)
    top30["종목명"] = names

    return top30, date_str


def _get_52week_high(ticker: str, base_date: str) -> tuple[str, float | None]:
    """해당 종목의 전일까지 52주 최고가 반환"""
    try:
        base  = datetime.datetime.strptime(base_date, "%Y%m%d").date()
        start = (base - datetime.timedelta(days=365)).strftime("%Y%m%d")
        # 당일 제외 → todate를 하루 전으로
        prev  = (base - datetime.timedelta(days=1)).strftime("%Y%m%d")
        df = stock.get_market_ohlcv_by_date(start, prev, ticker)
        if not df.empty:
            return ticker, float(df["고가"].max())
    except Exception as e:
        logger.warning(f"52주 고가 조회 실패 ({ticker}): {e}")
    return ticker, None


def _get_investor_data(ticker: str, date_str: str) -> tuple[str, dict]:
    """특정 종목의 투자자별 순매수 반환 (단위: 원)"""
    try:
        df = stock.get_market_trading_value_by_investor(date_str, date_str, ticker)
        if df.empty:
            return ticker, {}
        if "순매수" in df.columns:
            col = "순매수"
        elif len(df.columns) >= 3:
            col = df.columns[2]
        else:
            col = df.columns[-1]
        result = {}
        for inv in ["개인", "외국인", "기관합계", "연기금"]:
            if inv in df.index:
                result[inv] = float(df.loc[inv, col])
        return ticker, result
    except Exception as e:
        logger.warning(f"투자자 데이터 조회 실패 ({ticker}): {e}")
        return ticker, {}


def add_investor_data(df: pd.DataFrame, date_str: str) -> pd.DataFrame:
    """거래 주체별 순매수 데이터 컬럼 추가"""
    df = df.copy()
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_get_investor_data, t, date_str): t for t in df.index}
        investor_map: dict[str, dict] = {}
        for future in as_completed(futures):
            ticker, data = future.result()
            investor_map[ticker] = data
            time.sleep(0.1)
    df["투자자"] = [investor_map.get(t, {}) for t in df.index]
    return df


def add_52week_tags(df: pd.DataFrame, date_str: str) -> pd.DataFrame:
    """신고가돌파 / 신고가접근 태그 추가"""
    df = df.copy()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_get_52week_high, t, date_str): t for t in df.index}
        highs: dict[str, float | None] = {}
        for future in as_completed(futures):
            ticker, high = future.result()
            highs[ticker] = high
            time.sleep(0.05)

    tags, high_vals = [], []
    for ticker in df.index:
        high  = highs.get(ticker)
        close = float(df.loc[ticker, "종가"])
        if high:
            if close >= high:
                tags.append("신고가돌파")
            elif close >= high * 0.95:
                tags.append("신고가접근")
            else:
                tags.append("")
        else:
            tags.append("")
        high_vals.append(high)

    df["태그"]    = tags
    df["52주고가"] = high_vals
    return df


INDICATOR_SYMBOLS = {
    "VIX":    "^VIX",
    "DXY":    "DX-Y.NYB",
    "10Y":    "^TNX",
    "WTI":    "CL=F",
    "S&P500": "^GSPC",
    "NASDAQ": "^IXIC",
    "GOLD":   "GC=F",
    "USDKRW": "USDKRW=X",
}


def get_market_indicators() -> dict[str, pd.Series]:
    """8개 글로벌 지표 최근 3개월 종가 반환 (약 66 거래일)"""
    end   = datetime.date.today()
    start = end - datetime.timedelta(days=100)  # 충분한 여유 포함
    result = {}
    for name, sym in INDICATOR_SYMBOLS.items():
        try:
            hist = yf.Ticker(sym).history(
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
            )
            if not hist.empty:
                result[name] = hist["Close"].tail(66)   # 약 3개월
            else:
                logger.warning(f"{name} 데이터 없음")
        except Exception as e:
            logger.warning(f"{name} 조회 실패: {e}")
    return result
