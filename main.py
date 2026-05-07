import base64
import datetime
import logging
import smtplib
import sys
import time
from collections import defaultdict
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas_market_calendars as mcal

import config
from data_fetcher import (
    get_top30_stocks, add_52week_tags, add_investor_data, get_market_indicators
)
from sector_mapper import classify_sector
from news_scraper import fetch_sector_news
from chart_builder import build_market_chart, build_sector_chart, generate_commentary
from email_builder import build_html_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/daily.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

SECTOR_CHART_CID = "sector_chart.png"
MARKET_CHART_CID = "market_chart.png"


def _is_market_day() -> bool:
    """어제(KST 기준)가 한국 주식(XKRX) 개장일인지 확인."""
    KST = datetime.timezone(datetime.timedelta(hours=9))
    today_kst = datetime.datetime.now(KST).date()
    yesterday_kst = today_kst - datetime.timedelta(days=1)
    try:
        cal = mcal.get_calendar("XKRX")
        schedule = cal.schedule(
            start_date=yesterday_kst.isoformat(),
            end_date=yesterday_kst.isoformat(),
        )
        return not schedule.empty
    except Exception as e:
        logger.warning(f"XKRX 캘린더 조회 실패: {e}")
        return True  # 조회 실패 시 기본 발송


def _send_with_cid(user: str, password: str, to: list[str],
                   subject: str, html: str,
                   sector_b64: str, market_b64: str) -> None:
    """smtplib + multipart/related 로 CID 인라인 이미지 포함 발송."""
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"]    = user
    msg["To"]      = ", ".join(to)

    msg.attach(MIMEText(html, "html", "utf-8"))

    for cid, b64 in [(SECTOR_CHART_CID, sector_b64), (MARKET_CHART_CID, market_b64)]:
        if not b64:
            continue
        img = MIMEImage(base64.b64decode(b64), "png")
        img.add_header("Content-ID", f"<{cid}>")
        img.add_header("Content-Disposition", "inline", filename=cid)
        msg.attach(img)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(user, password)
        smtp.sendmail(user, to, msg.as_bytes())


def main():
    logger.info("=== 일일 주식 브리핑 시작 ===")

    # 거래일 확인 (한국 또는 미국 시장 열리는 날만 발송)
    if not _is_market_day():
        logger.info("오늘은 거래일이 아닙니다 (한국/미국 휴장). 발송 건너뜀.")
        sys.exit(0)

    # 1. 주식 데이터 수집
    logger.info("1) 거래대금 상위 30 종목 수집 중...")
    df, date_str = get_top30_stocks()
    logger.info(f"   기준일: {date_str}, 수집 종목 수: {len(df)}")

    # 2. 52주 고가 태그 추가
    logger.info("2) 52주 고가 분석 중 (약 30~60초 소요)...")
    df = add_52week_tags(df, date_str)

    # 3. 거래 주체 데이터 수집 (개인/외국인/기관/연기금)
    logger.info("3) 거래 주체 데이터 수집 중 (약 30초 소요)...")
    df = add_investor_data(df, date_str)

    # 4. 섹터 분류
    logger.info("4) 섹터 분류 중...")
    sector_data: dict[str, list[dict]] = defaultdict(list)
    for ticker, row in df.iterrows():
        name   = row["종목명"]
        sector = classify_sector(name, ticker)
        sector_data[sector].append({
            "ticker":   ticker,
            "종목명":   name,
            "거래대금": float(row["거래대금"]),
            "등락률":   float(row.get("등락률", 0.0)),
            "종가":     float(row["종가"]),
            "52주고가": row.get("52주고가"),
            "태그":     row.get("태그", ""),
            "투자자":   row.get("투자자") or {},
        })
    for sector, rows in sector_data.items():
        logger.info(f"   {sector}: {len(rows)}개")

    # 5. 섹터별 뉴스 수집
    logger.info("5) 섹터별 뉴스 수집 중...")
    sector_totals = {
        s: sum(r["거래대금"] for r in rows)
        for s, rows in sector_data.items()
    }
    top_sector = max(sector_totals, key=sector_totals.get) if sector_totals else None

    # 섹터 간 전역 중복 제거용 공유 집합 (규칙 2·5)
    global_seen_urls:   set[str]  = set()
    global_seen_titles: list[str] = []

    sector_news: dict[str, list[dict]] = {}
    for sector, rows in sector_data.items():
        count     = config.NEWS_COUNT_TOP_SECTOR if sector == top_sector else config.NEWS_COUNT_DEFAULT
        by_amount = sorted(rows, key=lambda x: x["거래대금"], reverse=True)
        top_tickers   = [r["ticker"]  for r in by_amount[:3]]
        top_companies = [r["종목명"] for r in by_amount[:3]]
        news = fetch_sector_news(
            sector, top_tickers, top_companies, count,
            date_str=date_str,
            global_seen_urls=global_seen_urls,
            global_seen_titles=global_seen_titles,
        )
        # 전역 seen 업데이트 → 이후 섹터에서 동일 기사 재사용 차단
        for art in news:
            global_seen_urls.add(art["url"])
            global_seen_titles.append(art["title"])
        sector_news[sector] = news
        logger.info(f"   {sector}: {len(news)}건 수집")
        time.sleep(0.5)

    # 6. 섹터 분포 차트
    logger.info("6) 섹터 분포 차트 생성 중...")
    sector_top_company = {
        s: max(rows, key=lambda r: r["거래대금"])["종목명"]
        for s, rows in sector_data.items() if rows
    }
    sector_chart_b64 = build_sector_chart(
        {s: sum(r["거래대금"] for r in rows) for s, rows in sector_data.items()},
        sector_top_company=sector_top_company,
    )

    # 7. 시장 지표 + 차트 + 코멘트
    logger.info("7) 글로벌 시장 지표 수집 중...")
    indicators       = get_market_indicators()
    market_chart_b64 = build_market_chart(indicators)
    commentary       = generate_commentary(indicators)
    logger.info(f"   수집된 지표: {list(indicators.keys())}")

    # 8. HTML 이메일 빌드
    logger.info("8) 이메일 HTML 생성 중...")
    html = build_html_email(
        sector_data=dict(sector_data),
        sector_news=sector_news,
        sector_chart_cid=SECTOR_CHART_CID if sector_chart_b64 else "",
        market_chart_cid=MARKET_CHART_CID if market_chart_b64 else "",
        commentary=commentary,
        date_str=date_str,
    )

    # 9. 이메일 발송 (smtplib CID 방식)
    logger.info("9) 이메일 발송 중...")
    if not config.EMAIL_PASSWORD:
        logger.error("GMAIL_APP_PASSWORD가 설정되지 않았습니다.")
        sys.exit(1)

    date_fmt = datetime.datetime.strptime(date_str, "%Y%m%d").strftime("%Y/%m/%d")
    subject  = f"📊 [{date_fmt}] 일일 주식 브리핑 — 거래대금 상위 30"

    try:
        _send_with_cid(
            user=config.EMAIL_USER,
            password=config.EMAIL_PASSWORD,
            to=config.EMAIL_TO,
            subject=subject,
            html=html,
            sector_b64=sector_chart_b64,
            market_b64=market_chart_b64,
        )
        logger.info(f"이메일 발송 완료 → {config.EMAIL_TO}")
    except Exception as e:
        logger.error(f"이메일 발송 실패: {e}")
        raise

    logger.info("=== 완료 ===")


if __name__ == "__main__":
    main()
