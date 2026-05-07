"""
HTML 이메일 빌더.
- <td>마다 명시적 background-color (Gmail/Outlook 호환)
- CID 이미지 참조 (cid:filename)
- 거래 주체 행 (개인/외인/기관)
- 뉴스 링크 display:block (모바일 탭 영역 확보)
"""
import datetime

# ── 포맷 헬퍼 ────────────────────────────────────────────────────────
def _fmt_amount(val: float) -> str:
    if val >= 1_000_000_000_000:
        return f"{val / 1_000_000_000_000:.1f}조"
    return f"{int(val / 100_000_000):,}억"

def _fmt_rate(val: float) -> str:
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%"

def _fmt_investor(val: float) -> str:
    abs_val = abs(val)
    sign = "+" if val > 0 else ("-" if val < 0 else "")
    if abs_val >= 1_000_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000_000:.1f}조"
    return f"{sign}{int(abs_val / 100_000_000):,}억"

# ── 팔레트 ───────────────────────────────────────────────────────────
BG_PAGE    = "#141929"
BG_CARD    = "#1c2540"
BG_HEADER  = "#1a2d52"
BG_TH      = "#1e3460"
BG_ROW     = "#1c2540"
BG_ROWALT  = "#212e4a"
BG_INV     = "#192338"
BG_NEWS    = "#172030"

C_TEXT     = "#e8f0f9"
C_SUB      = "#95b0c8"
C_UP       = "#ff7a7a"
C_DOWN     = "#6ab4ff"
C_BORDER   = "#2a3d56"
C_ACCENT   = "#40caff"
C_TAG_BRK  = "#ff6b35"
C_TAG_NEAR = "#ffb347"

TAG_HTML = {
    "신고가돌파": (
        f'<span style="display:inline-block;background:{C_TAG_BRK};color:#fff;'
        f'font-weight:700;font-size:10px;padding:2px 8px;border-radius:20px;'
        f'white-space:nowrap">🚀 신고가</span>'
    ),
    "신고가접근": (
        f'<span style="display:inline-block;background:{C_TAG_NEAR};color:#222;'
        f'font-weight:700;font-size:10px;padding:2px 8px;border-radius:20px;'
        f'white-space:nowrap">📈 근접</span>'
    ),
    "": "",
}

def _td(content, align="center", bold=False, color=None, bg=BG_ROW, extra=""):
    color = color or C_TEXT
    fw = "font-weight:700;" if bold else ""
    return (
        f'<td style="padding:9px 11px;text-align:{align};color:{color};'
        f'background-color:{bg};font-size:12px;border-bottom:1px solid {C_BORDER};'
        f'vertical-align:middle;{fw}{extra}">{content}</td>'
    )

def _investor_row(investor_data: dict, bg: str) -> str:
    if not investor_data:
        return ""
    parts = []
    for key, label in [("개인", "개인"), ("외국인", "외인"), ("기관합계", "기관")]:
        val = investor_data.get(key)
        if val is not None:
            col = C_UP if val > 0 else (C_DOWN if val < 0 else C_SUB)
            parts.append(
                f'<span style="color:{col};margin-right:12px;white-space:nowrap">'
                f'{label}&nbsp;{_fmt_investor(val)}</span>'
            )
    if not parts:
        return ""
    return (
        f'<tr><td colspan="6" style="padding:4px 12px 8px;font-size:11px;'
        f'background-color:{BG_INV};border-bottom:1px solid {C_BORDER}">'
        + "".join(parts) + '</td></tr>'
    )

def _ranking_table(all_stocks: list[dict]) -> str:
    """전체 거래대금 1~30위 요약표"""
    BG_H = "#1e3460"
    rows_html = ""
    for i, r in enumerate(all_stocks):
        bg       = BG_ROW if i % 2 == 0 else BG_ROWALT
        rank_col = "#fbbf24" if i < 3 else C_TEXT   # 1~3위 금색
        rate_col = C_UP if r["등락률"] > 0 else (C_DOWN if r["등락률"] < 0 else C_TEXT)
        tag      = TAG_HTML.get(r.get("태그", ""), "")

        rows_html += (
            f'<tr>'
            f'<td style="padding:7px 10px;text-align:center;color:{rank_col};font-weight:700;'
            f'font-size:13px;background-color:{bg};border-bottom:1px solid {C_BORDER}">{i+1}</td>'
            f'<td style="padding:7px 10px;color:{C_TEXT};font-weight:700;font-size:12px;'
            f'background-color:{bg};border-bottom:1px solid {C_BORDER}">{r["종목명"]}</td>'
            f'<td style="padding:7px 10px;text-align:center;color:{C_ACCENT};font-size:11px;'
            f'background-color:{bg};border-bottom:1px solid {C_BORDER};white-space:nowrap">{r.get("섹터","기타")}</td>'
            f'<td style="padding:7px 10px;text-align:center;color:{C_TEXT};font-size:12px;'
            f'background-color:{bg};border-bottom:1px solid {C_BORDER}">{_fmt_amount(r["거래대금"])}</td>'
            f'<td style="padding:7px 10px;text-align:center;color:{rate_col};font-weight:700;'
            f'font-size:12px;background-color:{bg};border-bottom:1px solid {C_BORDER}">{_fmt_rate(r["등락률"])}</td>'
            f'<td style="padding:7px 10px;text-align:center;background-color:{bg};'
            f'border-bottom:1px solid {C_BORDER}">{tag}</td>'
            f'</tr>'
        )

    header = (
        f'<tr style="background-color:{BG_H}">'
        f'<th style="padding:8px 10px;text-align:center;color:{C_ACCENT};font-size:11px;font-weight:700">#</th>'
        f'<th style="padding:8px 10px;text-align:left;color:{C_ACCENT};font-size:11px;font-weight:700">종목명</th>'
        f'<th style="padding:8px 10px;text-align:center;color:{C_ACCENT};font-size:11px;font-weight:700">섹터</th>'
        f'<th style="padding:8px 10px;text-align:center;color:{C_ACCENT};font-size:11px;font-weight:700">거래대금</th>'
        f'<th style="padding:8px 10px;text-align:center;color:{C_ACCENT};font-size:11px;font-weight:700">등락률</th>'
        f'<th style="padding:8px 10px;text-align:center;color:{C_ACCENT};font-size:11px;font-weight:700">태그</th>'
        f'</tr>'
    )

    return f"""
<table width="100%" cellpadding="0" cellspacing="0"
  style="border-radius:10px;margin-bottom:12px;border:1px solid {C_BORDER};border-collapse:separate;border-spacing:0">
  <tr>
    <td style="padding:13px 16px;background-color:{BG_HEADER};border-bottom:2px solid {C_BORDER};border-radius:10px 10px 0 0">
      <span style="font-size:15px;font-weight:700;color:#fff;border-left:4px solid {C_ACCENT};padding-left:9px">
        🏅 거래대금 순위 TOP 30
      </span>
    </td>
  </tr>
  <tr>
    <td style="padding:0;background-color:{BG_CARD};border-radius:0 0 10px 10px">
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
        <thead>{header}</thead>
        <tbody>{rows_html}</tbody>
      </table>
    </td>
  </tr>
</table>"""


def _sector_card(sector: str, rows: list[dict], news: list[dict], is_top: bool) -> str:
    sector_amount = sum(r["거래대금"] for r in rows)
    top_badge = (
        f'&nbsp;<span style="background:#ea580c;color:#fff;font-size:10px;'
        f'font-weight:700;padding:2px 7px;border-radius:4px">🏆&nbsp;1위</span>'
        if is_top else ""
    )

    # ─ 종목 행 ─
    table_rows = ""
    for i, r in enumerate(rows):
        bg = BG_ROW if i % 2 == 0 else BG_ROWALT
        rate_color = C_UP if r["등락률"] > 0 else (C_DOWN if r["등락률"] < 0 else C_TEXT)
        h52  = r.get("52주고가")
        high = f"{int(h52):,}" if h52 and h52 == h52 else "-"
        tag  = TAG_HTML.get(r.get("태그", ""), "")
        table_rows += f"""<tr>
          {_td(r['종목명'], align='left', bold=True, bg=bg)}
          {_td(_fmt_amount(r['거래대금']), bg=bg)}
          {_td(_fmt_rate(r['등락률']), color=rate_color, bold=True, bg=bg)}
          {_td(f"{int(r['종가']):,}", bg=bg)}
          {_td(high, bg=bg)}
          <td style="padding:6px 11px;text-align:center;background-color:{bg};
                     border-bottom:1px solid {C_BORDER};vertical-align:middle">{tag}</td>
        </tr>"""
        table_rows += _investor_row(r.get("투자자") or {}, bg)

    # ─ 뉴스 ─
    news_items = ""
    for n in news:
        src = (
            f'<span style="display:inline-block;font-size:10px;background:#1e3a50;'
            f'color:{C_ACCENT};padding:1px 6px;border-radius:3px;'
            f'margin-right:6px;white-space:nowrap">{n["source"]}</span>'
            if n.get("source") else ""
        )
        news_items += (
            f'<a href="{n["url"]}" target="_blank" style="display:block;'
            f'padding:9px 0;border-bottom:1px solid {C_BORDER};'
            f'color:{C_ACCENT};text-decoration:none;font-size:13px;line-height:1.45">'
            f'{src}{n["title"][:78]}</a>'
        )
    if not news_items:
        news_items = f'<div style="color:{C_SUB};font-size:13px;padding:8px 0">뉴스를 가져오지 못했습니다.</div>'

    news_label = f"관련 뉴스 {'(5건 — 거래대금 1위 섹터)' if is_top else '(3건)'}"

    return f"""
<table width="100%" cellpadding="0" cellspacing="0"
  style="border-radius:10px;margin-bottom:12px;border:1px solid {C_BORDER};border-collapse:separate;border-spacing:0">
  <!-- 카드 헤더 -->
  <tr>
    <td style="padding:13px 16px;background-color:{BG_HEADER};
               border-bottom:2px solid {C_BORDER};border-radius:10px 10px 0 0">
      <span style="font-size:15px;font-weight:700;color:#ffffff;
                   border-left:4px solid {C_ACCENT};padding-left:9px">{sector}{top_badge}</span>
      <span style="float:right;color:{C_SUB};font-size:12px">총 {_fmt_amount(sector_amount)}</span>
    </td>
  </tr>
  <!-- 종목 표 -->
  <tr>
    <td style="padding:0;background-color:{BG_CARD}">
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
        <thead>
          <tr>
            <th style="padding:8px 11px;text-align:left;color:{C_ACCENT};background-color:{BG_TH};font-size:11px;font-weight:700">종목명</th>
            <th style="padding:8px 11px;text-align:center;color:{C_ACCENT};background-color:{BG_TH};font-size:11px;font-weight:700">거래대금</th>
            <th style="padding:8px 11px;text-align:center;color:{C_ACCENT};background-color:{BG_TH};font-size:11px;font-weight:700">등락률</th>
            <th style="padding:8px 11px;text-align:center;color:{C_ACCENT};background-color:{BG_TH};font-size:11px;font-weight:700">종가</th>
            <th style="padding:8px 11px;text-align:center;color:{C_ACCENT};background-color:{BG_TH};font-size:11px;font-weight:700">52주고가</th>
            <th style="padding:8px 11px;text-align:center;color:{C_ACCENT};background-color:{BG_TH};font-size:11px;font-weight:700">태그</th>
          </tr>
        </thead>
        <tbody>{table_rows}</tbody>
      </table>
    </td>
  </tr>
  <!-- 뉴스 -->
  <tr>
    <td style="padding:12px 16px;background-color:{BG_NEWS};border-top:1px solid {C_BORDER};border-radius:0 0 10px 10px">
      <div style="font-size:11px;font-weight:700;color:{C_SUB};letter-spacing:0.8px;
                  text-transform:uppercase;margin-bottom:6px">{news_label}</div>
      {news_items}
    </td>
  </tr>
</table>"""


def build_html_email(
    sector_data:      dict[str, list[dict]],
    sector_news:      dict[str, list[dict]],
    sector_chart_cid: str,
    market_chart_cid: str,
    commentary:       str,
    date_str:         str,
) -> str:
    sector_totals  = {
        s: sum(r["거래대금"] for r in rows)
        for s, rows in sector_data.items() if rows
    }
    sorted_sectors = sorted(sector_totals, key=sector_totals.get, reverse=True)
    top_sector     = sorted_sectors[0] if sorted_sectors else None
    total_all      = sum(sector_totals.values())
    date_fmt       = datetime.datetime.strptime(date_str, "%Y%m%d").strftime("%Y년 %m월 %d일")

    # 전체 30위 순위표 구성
    all_stocks = []
    for sector, rows in sector_data.items():
        for r in rows:
            all_stocks.append({**r, "섹터": sector})
    all_stocks.sort(key=lambda x: x["거래대금"], reverse=True)
    ranking_html = _ranking_table(all_stocks)

    # 섹터 카드
    cards_html = ""
    for sector in sorted_sectors:
        rows = sorted(sector_data[sector], key=lambda r: r["거래대금"], reverse=True)
        cards_html += _sector_card(
            sector, rows, sector_news.get(sector, []),
            is_top=(sector == top_sector),
        )

    # 섹터 분포 차트 블록
    sector_chart_html = ""
    if sector_chart_cid:
        sector_chart_html = f"""
<table width="100%" cellpadding="0" cellspacing="0"
  style="border-radius:10px;margin-bottom:12px;border:1px solid {C_BORDER};border-collapse:separate;border-spacing:0">
  <tr>
    <td style="padding:13px 16px;background-color:{BG_HEADER};border-bottom:2px solid {C_BORDER};border-radius:10px 10px 0 0">
      <span style="font-size:15px;font-weight:700;color:#fff;border-left:4px solid {C_ACCENT};padding-left:9px">
        📊 섹터별 거래대금 분포
      </span>
    </td>
  </tr>
  <tr>
    <td style="padding:14px 16px;background-color:{BG_CARD};border-radius:0 0 10px 10px">
      <img src="cid:{sector_chart_cid}" width="100%"
           style="max-width:880px;border-radius:6px;display:block">
    </td>
  </tr>
</table>"""

    # 시장 지표 차트 + 코멘트
    market_chart_html = ""
    if market_chart_cid:
        market_chart_html = (
            f'<img src="cid:{market_chart_cid}" width="100%"'
            f' style="max-width:880px;border-radius:6px;display:block;margin-bottom:14px">'
        )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>일일 주식 브리핑 {date_fmt}</title>
</head>
<body style="margin:0;padding:14px;background-color:{BG_PAGE};
             font-family:'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:940px;margin:0 auto">

  <!-- ① 헤더 -->
  <tr>
    <td style="background-color:{BG_HEADER};color:#fff;
               padding:22px 28px;border-radius:10px;
               border:1px solid {C_BORDER}">
      <div style="font-size:20px;font-weight:700;margin-bottom:5px">📊 일일 주식 시장 브리핑</div>
      <div style="font-size:12px;color:{C_SUB}">
        {date_fmt} 기준 &nbsp;·&nbsp; 거래대금 상위 30개 종목 &nbsp;·&nbsp; 전체 합산 {_fmt_amount(total_all)}
      </div>
    </td>
  </tr>
  <tr><td style="height:12px;background-color:{BG_PAGE}"></td></tr>

  <!-- ② 섹터 분포 차트 (트리맵) -->
  <tr><td style="background-color:{BG_PAGE}">{sector_chart_html}</td></tr>

  <!-- ③ 전체 30위 순위표 -->
  <tr><td style="background-color:{BG_PAGE}">{ranking_html}</td></tr>

  <!-- ④ 섹터 카드 -->
  <tr><td style="background-color:{BG_PAGE}">{cards_html}</td></tr>

  <!-- ④ 글로벌 지표 -->
  <tr>
    <td style="background-color:{BG_CARD};border-radius:10px;padding:16px 18px;
               border:1px solid {C_BORDER}">
      <div style="font-size:15px;font-weight:700;color:#fff;
                  border-left:4px solid {C_ACCENT};padding-left:9px;margin-bottom:12px">
        🌐 글로벌 시장 지표 (최근 3개월)
      </div>
      {market_chart_html}
      <!-- 전문가 코멘트 표 -->
      <div style="font-size:13px;font-weight:700;color:#81c784;margin-bottom:8px">📝 지표별 해석</div>
      {commentary}
    </td>
  </tr>
  <tr><td style="height:10px;background-color:{BG_PAGE}"></td></tr>

  <!-- ⑤ 푸터 -->
  <tr>
    <td style="text-align:center;font-size:11px;color:{C_SUB};padding:14px 0;background-color:{BG_PAGE}">
      본 메일은 자동으로 발송되었습니다. 투자 판단은 본인 책임입니다.
    </td>
  </tr>

</table>
</body>
</html>"""
