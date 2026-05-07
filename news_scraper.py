"""
뉴스 수집 — 5가지 품질 기준:
  1. 관련성 게이트: 섹터 키워드 또는 기업명이 제목에 포함 (필수조건)
  2. 기준일 필터: 거래 기준일(KST) 이전 기사 제외 (Naver 종목 뉴스 제외)
  3. 공신력 소스: Naver Finance API + 주요 경제지 RSS
  4. 섹터 내 중복 제거: URL + 제목 유사도 Jaccard 0.65
  5. 섹터 간 중복 제거: URL 완전일치 + 제목 유사도 Jaccard 0.80 (더 엄격)
"""
import logging
import re
import time
import random
import datetime
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}
TIMEOUT = 8

# 공신력 있는 경제지 RSS 피드 (동작 확인된 피드만)
RSS_FEEDS = [
    ("연합뉴스", "https://www.yna.co.kr/rss/economy.xml"),
    ("매일경제", "https://www.mk.co.kr/rss/30100041/"),
    ("한국경제", "https://www.hankyung.com/feed/economy"),
    ("전자신문", "https://rss.etnews.com/Section901.xml"),
]

# 주가 움직임 원인 키워드
PRICE_KEYWORDS = [
    "급등", "급락", "상승", "하락", "강세", "약세",
    "수주", "계약", "호재", "악재", "실적", "어닝",
    "전망", "목표가", "투자의견", "매수", "돌파", "신고가",
]

# ── 34개 세분화 섹터별 핵심 검색 키워드 ──────────────────────────────────
SECTOR_SEARCH_KEYWORDS: dict[str, list[str]] = {
    "메모리반도체":       ["D램", "낸드", "HBM", "DRAM", "NAND", "삼성전자", "SK하이닉스", "반도체"],
    "반도체전공정장비":   ["전공정", "CVD", "ALD", "식각장비", "증착장비", "원익IPS", "한미반도체", "반도체장비"],
    "반도체후공정장비":   ["후공정", "검사장비", "본딩", "이오테크닉스", "테크윙", "파크시스템스"],
    "반도체소재":         ["포토레지스트", "웨이퍼소재", "반도체소재", "동진쎄미켐", "솔브레인"],
    "팹리스/시스템반도체":["팹리스", "시스템반도체", "AP칩", "SoC", "DB하이텍", "가온칩스"],
    "반도체패키징/기판":  ["패키징", "반도체기판", "CoWoS", "HBM기판", "하나마이크론", "심텍"],
    "2차전지셀":          ["배터리셀", "원통형전지", "파우치셀", "LG에너지솔루션", "삼성SDI", "SK이노베이션"],
    "2차전지소재":        ["양극재", "음극재", "전해질", "분리막", "에코프로", "포스코퓨처엠", "엘앤에프"],
    "2차전지장비/부품":   ["배터리장비", "전지장비", "권취", "씨아이에스", "피엔티"],
    "완성차":             ["현대차", "기아", "완성차", "전기차수출", "자동차판매"],
    "자동차부품":         ["자동차부품", "타이어", "현대모비스", "만도", "한국타이어"],
    "바이오":             ["바이오", "항체", "ADC", "바이오시밀러", "항암제", "삼성바이오", "셀트리온", "알테오젠"],
    "제약":               ["제약", "의약품", "신약", "임상시험", "FDA", "한미약품", "유한양행"],
    "의료기기/뷰티테크":  ["의료기기", "보툴리눔", "필러", "뷰티테크", "휴젤", "메디톡스", "클래시스"],
    "방산":               ["방산", "K방산", "유도탄", "전차", "한화에어로", "LIG넥스원", "현대로템"],
    "조선":               ["조선", "LNG선", "LPG선", "수주잔고", "HD현대중공업", "삼성중공업", "한화오션"],
    "우주항공":           ["우주", "위성", "발사체", "항공우주", "누리호", "한국항공우주"],
    "원전/발전설비":      ["원전", "원자력", "SMR", "핵융합", "두산에너빌리티", "한전기술"],
    "전력인프라":         ["변압기", "전력인프라", "송배전", "HVDC", "전선", "LS ELECTRIC", "산일전기"],
    "태양광/친환경":      ["태양광", "태양전지", "재생에너지", "한화솔루션", "씨에스윈드"],
    "수소/풍력":          ["수소", "풍력", "연료전지", "그린수소", "해상풍력", "두산퓨얼셀"],
    "은행/금융지주":      ["금융지주", "은행", "NIM", "대출금리", "KB금융", "신한지주", "하나금융"],
    "보험":               ["보험", "생명보험", "손해보험", "삼성생명", "삼성화재", "메리츠화재"],
    "증권":               ["증권", "자산운용", "IB", "미래에셋", "키움증권", "NH투자증권"],
    "플랫폼/인터넷":      ["네이버", "카카오", "포털", "플랫폼", "카카오페이", "카카오뱅크"],
    "IT서비스/전자":      ["LG전자", "LG이노텍", "삼성SDS", "IT서비스", "디스플레이"],
    "게임":               ["게임", "e스포츠", "모바일게임", "엔씨소프트", "크래프톤", "넥슨"],
    "엔터/미디어":        ["K팝", "아이돌", "음원", "드라마", "HYBE", "SM엔터", "JYP", "YG"],
    "통신장비":           ["광통신", "안테나", "통신장비", "기지국", "쏠리드", "케이엠더블유"],
    "통신서비스":         ["SK텔레콤", "KT", "LG유플러스", "이동통신", "5G서비스"],
    "철강/금속":          ["철강", "포스코", "제철", "스틸", "고려아연", "현대제철"],
    "화학":               ["화학", "케미칼", "정유", "석유화학", "LG화학", "롯데케미칼"],
    "건설":               ["건설", "분양", "시공", "수주잔고", "현대건설", "GS건설"],
    "로봇/자동화":        ["로봇", "로보틱스", "휴머노이드", "두산로보틱스", "레인보우로보틱스"],
    "기타":               ["코스피", "코스닥", "증시", "주식시장"],
}


# ── Naver Finance 종목별 뉴스 API ─────────────────────────────────────
def _fetch_naver_stock_news(ticker: str, count: int) -> list[dict]:
    url = f"https://m.stock.naver.com/api/news/stock/{ticker}?pageSize={count}&page=1"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
        # 응답 형식: [{total, items:[{실제기사}]}] 또는 [{실제기사}]
        raw_items: list = []
        if isinstance(data, list):
            for group in data:
                if isinstance(group, dict) and "items" in group:
                    raw_items.extend(group["items"])   # 중첩 구조
                elif isinstance(group, dict) and "title" in group:
                    raw_items.append(group)             # 직접 기사 목록
        elif isinstance(data, dict):
            raw_items = data.get("items", data.get("list", []))

        results = []
        for item in raw_items[:count]:
            title = item.get("titleFull") or item.get("title", "")
            link  = (item.get("mobileNewsUrl") or item.get("url")
                     or item.get("link", ""))
            src   = item.get("officeName", "네이버금융")
            if title and link and link.startswith("http"):
                results.append({
                    "title":    title,
                    "url":      link,
                    "source":   src,
                    "pub_dt":   datetime.datetime.now(datetime.timezone.utc),
                    "is_naver": True,
                })
        return results
    except Exception as e:
        logger.debug(f"Naver stock news 실패 ({ticker}): {e}")
        return []


# ── RSS 수집 ──────────────────────────────────────────────────────────
def _parse_pubdate(item) -> datetime.datetime | None:
    tag = item.select_one("pubDate")
    if not tag:
        return None
    try:
        dt = parsedate_to_datetime(tag.get_text(strip=True))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        return None


def _fetch_rss(feed_url: str, feed_name: str) -> list[dict]:
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        items = []
        for item in soup.select("item"):
            title_tag = item.select_one("title")
            link_tag  = item.select_one("link")
            title = title_tag.get_text(strip=True) if title_tag else ""
            link  = ""
            if link_tag:
                link = link_tag.get_text(strip=True)
                if not link:
                    sib  = link_tag.next_sibling
                    link = str(sib).strip() if sib else ""
            if title and link and link.startswith("http"):
                items.append({
                    "title":    title,
                    "url":      link,
                    "source":   feed_name,
                    "pub_dt":   _parse_pubdate(item),
                    "is_naver": False,
                })
        return items
    except Exception as e:
        logger.warning(f"RSS 수집 실패 [{feed_name}]: {e}")
        return []


# ── 규칙 1: 관련성 게이트 ─────────────────────────────────────────────
def _is_relevant(art: dict, sector_kws: list[str], company_names: list[str]) -> bool:
    """섹터 키워드 또는 기업명이 제목에 포함되어야 함.
    Naver 종목 뉴스는 주가 움직임 키워드만 있어도 통과 (종목 전용 피드 컨텍스트)."""
    title = art["title"]
    for kw in sector_kws:
        if kw in title:
            return True
    for name in company_names:
        if len(name) >= 2 and name in title:
            return True
    # Naver 종목 뉴스에 한해: 주가 관련 키워드 포함 시 허용
    if art.get("is_naver"):
        for kw in PRICE_KEYWORDS:
            if kw in title:
                return True
    return False


# ── 규칙 2: 기준일 필터 (KST 기준) ───────────────────────────────────
def _is_recent(art: dict, cutoff_date_str: str) -> bool:
    """Naver 뉴스는 항상 최신. RSS는 KST 기준 기준일 자정 이후만 허용."""
    if art.get("is_naver"):
        return True
    pub_dt = art.get("pub_dt")
    if not pub_dt or not cutoff_date_str:
        return True
    try:
        kst    = datetime.timezone(datetime.timedelta(hours=9))
        cutoff = datetime.datetime.strptime(cutoff_date_str, "%Y%m%d").replace(
            tzinfo=kst
        ).astimezone(datetime.timezone.utc)
        return pub_dt >= cutoff
    except Exception:
        return True


# ── 점수 산정 ─────────────────────────────────────────────────────────
def _score_article(art: dict, sector_kws: list[str], company_names: list[str]) -> int:
    title = art["title"]
    score = 0

    # 기업명 포함 (가장 직접적 관련성, 최대 3개)
    for name in company_names[:3]:
        if len(name) >= 2 and name in title:
            score += 5

    # 섹터 핵심 키워드 (1번째 +4, 이후 +2)
    for i, kw in enumerate(sector_kws):
        if kw in title:
            score += 4 if i == 0 else 2

    # 주가 움직임 원인 키워드 (+2/개, 최대 +6)
    pk_bonus = 0
    for kw in PRICE_KEYWORDS:
        if kw in title:
            pk_bonus += 2
        if pk_bonus >= 6:
            break
    score += pk_bonus

    # 최신성 가중치
    pub_dt = art.get("pub_dt")
    if pub_dt:
        age_h = (datetime.datetime.now(datetime.timezone.utc) - pub_dt).total_seconds() / 3600
        if age_h < 6:
            score += 8
        elif age_h < 24:
            score += 5
        elif age_h < 48:
            score += 2

    return score


# ── 제목 유사도 중복 판단 ─────────────────────────────────────────────
def _titles_similar(t1: str, t2: str, threshold: float) -> bool:
    tokens1 = set(re.findall(r'[가-힣a-zA-Z0-9]+', t1))
    tokens2 = set(re.findall(r'[가-힣a-zA-Z0-9]+', t2))
    if not tokens1 or not tokens2:
        return False
    overlap = len(tokens1 & tokens2)
    union   = len(tokens1 | tokens2)
    return overlap / union >= threshold


# ── 메인 수집 함수 ────────────────────────────────────────────────────
def fetch_sector_news(
    sector:             str,
    top_tickers:        list[str],
    top_companies:      list[str],
    count:              int,
    date_str:           str = "",          # 규칙 2: 기준일 (YYYYMMDD)
    global_seen_urls:   set | None = None, # 규칙 5: 섹터 간 URL 중복 제거
    global_seen_titles: list | None = None,# 규칙 5: 섹터 간 제목 중복 제거
) -> list[dict]:
    sector_kws  = SECTOR_SEARCH_KEYWORDS.get(sector, [sector])
    _g_urls     = global_seen_urls   or set()
    _g_titles   = global_seen_titles or []

    # ① Naver Finance 종목별 뉴스 (상위 3 종목, 각 5건) — 항상 관련성 보장
    all_articles: list[dict] = []
    for ticker in top_tickers[:3]:
        naver_news = _fetch_naver_stock_news(ticker, 5)
        all_articles.extend(naver_news)
        time.sleep(0.3)

    # ② RSS 피드
    for feed_name, feed_url in RSS_FEEDS:
        articles = _fetch_rss(feed_url, feed_name)
        all_articles.extend(articles)
        time.sleep(random.uniform(0.1, 0.25))

    # ─ 규칙 1: 관련성 게이트 ─
    relevant = [a for a in all_articles if _is_relevant(a, sector_kws, top_companies)]

    # ─ 규칙 2: 기준일 필터 ─
    if date_str:
        relevant = [a for a in relevant if _is_recent(a, date_str)]

    # ─ 점수 산정 후 내림차순 정렬 ─
    for art in relevant:
        art["score"] = _score_article(art, sector_kws, top_companies)
    relevant.sort(key=lambda x: x["score"], reverse=True)

    # ─ 중복 제거 (규칙 4·5) ─
    # 섹터 내 중복: Jaccard 0.65 (엄격)
    # 섹터 간 중복: URL 완전일치 + Jaccard 0.80 (느슨 — 다른 기업 비슷한 형식 허용)
    local_titles: list[str] = []   # 이번 섹터에서 추가된 제목만
    results: list[dict] = []

    for art in relevant:
        url   = art["url"]
        title = art["title"]

        # 섹터 간 URL 중복 (규칙 5)
        if url in _g_urls:
            continue

        # 섹터 간 제목 유사도 (규칙 5 — 임계값 0.80)
        if any(_titles_similar(title, t, 0.80) for t in _g_titles):
            continue

        # 섹터 내 제목 유사도 (규칙 4 — 임계값 0.65)
        if any(_titles_similar(title, t, 0.65) for t in local_titles):
            continue

        local_titles.append(title)
        results.append(art)
        if len(results) >= count:
            break

    return results[:count]
