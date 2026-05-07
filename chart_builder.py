import base64
import io
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import squarify

logger = logging.getLogger(__name__)

plt.rcParams.update({
    "font.family":        ["NanumGothic", "AppleGothic", "Arial Unicode MS", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "text.color":         "#e8f0f9",
})

# ── 지표 설정 ────────────────────────────────────────────────────────
INDICATOR_CONFIG = {
    "VIX":    {"label": "VIX (공포지수)",     "color": "#e53935", "unit": ""},
    "DXY":    {"label": "달러인덱스 DXY",     "color": "#1e88e5", "unit": ""},
    "10Y":    {"label": "미 10년물 금리(%)",  "color": "#43a047", "unit": "%"},
    "WTI":    {"label": "WTI 유가($/배럴)",  "color": "#fb8c00", "unit": "$"},
    "S&P500": {"label": "S&P 500",           "color": "#8e24aa", "unit": ""},
    "NASDAQ": {"label": "NASDAQ",            "color": "#00acc1", "unit": ""},
    "GOLD":   {"label": "금($/oz)",          "color": "#f9a825", "unit": "$"},
    "USDKRW": {"label": "원달러 환율(₩)",    "color": "#6d4c41", "unit": "₩"},
}
INDICATOR_ORDER = ["VIX", "DXY", "10Y", "WTI", "S&P500", "NASDAQ", "GOLD", "USDKRW"]

# ── 섹터 색상 (34개 + 기타) ──────────────────────────────────────────
SECTOR_COLORS = {
    # 반도체 계열 — 파란색 계열
    "메모리반도체":       "#1976d2",
    "반도체전공정장비":   "#2196f3",
    "반도체후공정장비":   "#42a5f5",
    "반도체소재":         "#64b5f6",
    "팹리스/시스템반도체":"#29b6f6",
    "반도체패키징/기판":  "#26c6da",
    # 2차전지 — 초록색 계열
    "2차전지셀":          "#2e7d32",
    "2차전지소재":        "#43a047",
    "2차전지장비/부품":   "#66bb6a",
    # 자동차 — 청록색 계열
    "완성차":             "#00897b",
    "자동차부품":         "#26a69a",
    # 바이오/제약 — 빨간색 계열
    "바이오":             "#e53935",
    "제약":               "#ef5350",
    "의료기기/뷰티테크":  "#ff7043",
    # 방산/우주/조선 — 남색/회청 계열
    "방산":               "#5c6bc0",
    "조선":               "#546e7a",
    "우주항공":           "#3949ab",
    # 에너지 — 오렌지 계열
    "원전/발전설비":      "#e65100",
    "전력인프라":         "#f57c00",
    "태양광/친환경":      "#fb8c00",
    "수소/풍력":          "#ffa726",
    # 금융 — 보라색 계열
    "은행/금융지주":      "#7b1fa2",
    "보험":               "#9c27b0",
    "증권":               "#ba68c8",
    # IT — 밝은 청색 계열
    "플랫폼/인터넷":      "#0288d1",
    "IT서비스/전자":      "#039be5",
    "게임":               "#00acc1",
    "엔터/미디어":        "#00838f",
    "통신장비":           "#00796b",
    "통신서비스":         "#009688",
    # 소재/인프라 — 중성 계열
    "철강/금속":          "#78909c",
    "화학":               "#8bc34a",
    "건설":               "#a1887f",
    "로봇/자동화":        "#ab47bc",
    "기타":               "#9e9e9e",
}


# ── 시장 지표 차트 ───────────────────────────────────────────────────
def _sparkline_ax(ax, data: pd.Series, cfg: dict) -> None:
    ax.set_facecolor("#202c4a")
    ax.set_title(cfg["label"], fontsize=10, fontweight="bold", color="#e8f0f9", pad=5)
    for spine in ax.spines.values():
        spine.set_color("#3a4570")
    ax.tick_params(colors="#99b0cc", labelsize=7)
    ax.grid(axis="y", linestyle="--", alpha=0.3, color="#4a5f80")

    if data.empty or len(data) < 2:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                transform=ax.transAxes, color="#99b0cc")
        return

    x, color = range(len(data)), cfg["color"]
    ax.plot(x, data.values, color=color, linewidth=2, marker="o", markersize=3, zorder=3)
    ax.fill_between(x, data.values, alpha=0.20, color=color)

    last = data.iloc[-1]
    ax.annotate(f"{cfg['unit']}{last:,.2f}", xy=(len(data)-1, last),
                xytext=(-5, 5), textcoords="offset points",
                fontsize=9, fontweight="bold", color=color)

    step     = max(1, len(data) // 4)
    tick_pos = list(range(0, len(data), step))
    ax.set_xticks(tick_pos)
    ax.set_xticklabels([data.index[i].strftime("%m/%d") for i in tick_pos],
                       rotation=30, ha="right", color="#99b0cc")

    chg = last - data.iloc[0]
    ax.set_xlabel(f"{'▲' if chg >= 0 else '▼'} {abs(chg):.2f}  (3개월 변화)",
                  color="#ff7a7a" if chg >= 0 else "#6ab4ff", fontsize=7.5)


def build_market_chart(indicators: dict[str, pd.Series]) -> str:
    fig, axes = plt.subplots(2, 4, figsize=(16, 7))
    fig.patch.set_facecolor("#1b2540")
    fig.suptitle("글로벌 시장 지표 — 최근 3개월", fontsize=13,
                 fontweight="bold", color="#e8f0f9", y=1.01)
    for ax, key in zip(axes.flat, INDICATOR_ORDER):
        _sparkline_ax(ax, indicators.get(key, pd.Series(dtype=float)), INDICATOR_CONFIG[key])
    plt.tight_layout(pad=2.0)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


# ── 섹터 트리맵 ──────────────────────────────────────────────────────
def build_sector_chart(
    sector_totals:     dict[str, float],
    sector_top_company: dict[str, str] | None = None,
) -> str:
    if not sector_totals:
        return ""
    sector_top_company = sector_top_company or {}

    # 내림차순 정렬 (squarify는 큰 값을 좌상단에)
    sorted_items = sorted(sector_totals.items(), key=lambda x: x[1], reverse=True)
    labels  = [s for s, _ in sorted_items]
    values  = [v / 1e8 for _, v in sorted_items]   # 억원
    total   = sum(values)
    colors  = [SECTOR_COLORS.get(l, "#607d8b") for l in labels]

    # 라벨 — 큰 섹터: 섹터명 + 대표기업 + 금액/비율, 중간: 섹터+기업, 작은: 섹터명만
    threshold_lg = total * 0.06   # 6% 이상: 상세 표시
    threshold_md = total * 0.02   # 2~6%: 섹터+기업명
    tile_labels = []
    for lbl, val in zip(labels, values):
        pct     = val / total * 100
        company = sector_top_company.get(lbl, "")
        comp_ln = f"\n{company}" if company else ""
        if pct >= threshold_lg / total * 100:
            tile_labels.append(f"{lbl}{comp_ln}\n{val:,.0f}억  ({pct:.1f}%)")
        elif pct >= threshold_md / total * 100:
            tile_labels.append(f"{lbl}{comp_ln}")
        else:
            tile_labels.append(lbl if pct >= 1.0 else "")

    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor("#161f38")
    ax.set_facecolor("#161f38")

    squarify.plot(
        sizes=values,
        label=tile_labels,
        color=colors,
        alpha=0.90,
        ax=ax,
        text_kwargs={
            "fontsize": 9, "color": "white", "fontweight": "bold",
            "multialignment": "center",
        },
        pad=True,
    )
    ax.axis("off")
    ax.set_title("섹터별 거래대금 분포 (트리맵)", fontsize=13,
                 fontweight="bold", color="#e8f0f9", pad=10)

    # 범례 (소규모 섹터 식별용)
    patches = [mpatches.Patch(color=SECTOR_COLORS.get(l, "#607d8b"), label=l)
               for l in labels if (values[labels.index(l)] / total * 100) < 4]
    if patches:
        ax.legend(handles=patches, loc="lower right", fontsize=7,
                  facecolor="#202c4a", edgecolor="#3a4570",
                  labelcolor="white", ncol=2, framealpha=0.9)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


# ── 전문가 코멘트 — HTML 표 ──────────────────────────────────────────
def generate_commentary(indicators: dict[str, pd.Series]) -> str:
    BORDER = "#2a3d56"
    C_KEY  = "#56d4f5"
    C_VAL  = "#f0f6ff"
    C_SUB  = "#b8cee0"
    C_UP   = "#ff7a7a"
    C_DN   = "#6ab4ff"
    BG_ROW = "#1c2a3e"
    BG_ALT = "#1f3048"

    def _r(key):
        d = indicators.get(key)
        if d is None or len(d) < 2:
            return None
        return d.iloc[-1], d.iloc[-1] - d.iloc[0]

    def _pct(v, c):
        base = v - c
        return f"{c / base * 100:+.1f}%" if base != 0 else "N/A"

    specs = [
        ("VIX", "VIX 공포지수", "", 2, lambda v, c: (
            "🔴 극도 공포(30↑) — 패닉 매도 구간. 역사적으로 VIX 35↑는 역발상 매수 기회로 이어진 경우 많음. "
            "단, 유동성 위기 동반 시 추가 하락 가능 → 분할 매수·손절 기준 재확인 필요."
            if v > 30 else
            "🟠 공포 구간(20~30) — 변동성 확대 국면. 포지션 축소·손절매 기준 재점검 권장. "
            "방어주(금·채권·배당주) 비중 확대 고려. 이벤트(FOMC·실적) 전후 스파이크 대비."
            if v > 20 else
            "🟡 중립(15~20) — 방향성 불명확한 횡보 가능성. "
            "이벤트 전후 VIX 급등 가능성 존재 → 옵션 헤지 또는 현금 비중 유지 전략."
            if v > 15 else
            "🟢 안정(15↓) — 시장 과신 경계 구간. VIX 극저점은 역사적으로 급락 직전 신호인 경우 있음. "
            "포트폴리오 리밸런싱 및 익절 검토 시점."
        )),
        ("DXY", "달러인덱스 DXY", "", 1, lambda v, c: (
            f"📈 달러 강세(3개월 {_pct(v,c)}) — 신흥국 자금 유출·원자재 하방 압력. "
            "한국 수출 대형주 환차익은 있으나 외국인 원화 자산 매도 우려. "
            "달러 강세 수혜: IT부품 수출주·달러 매출 비중 높은 기업."
            if c > 0 else
            f"📉 달러 약세(3개월 {_pct(v,c)}) — 신흥국 자금 유입·원자재 지지. "
            "외국인 한국 주식 순매수 유인 증가 기대. "
            "수혜 업종: 비철금속·에너지·신흥국 소비재."
        )),
        ("10Y", "미 10년물 금리", "%", 2, lambda v, c: (
            f"📈 금리 상승({v:.2f}%, 3개월 +{abs(c):.2f}%p) — 성장주(바이오·플랫폼·2차전지) 밸류에이션 압박. "
            "PER 고평가 종목 리레이팅 리스크 증가. 배당주·가치주 상대 강세 예상. "
            "4.5% 이상 구간은 경기침체 우려 현실화 신호로 해석."
            if c > 0.1 else
            f"📉 금리 하락({v:.2f}%, 3개월 {_pct(v,c)}) — 성장주 밸류에이션 부담 완화. "
            "반도체·바이오 등 장기 성장주 재부각 가능. "
            "채권 가격 동반 상승 → 채권 ETF·금리 민감 업종 주목."
            if c < -0.1 else
            f"➡️ 금리 횡보({v:.2f}%) — 뚜렷한 방향성 없음. "
            "FOMC 결과 또는 고용·물가 데이터 확인 후 섹터 로테이션 전략 구사."
        )),
        ("WTI", "WTI 유가", "$", 1, lambda v, c: (
            f"📈 유가 급등(${v:.1f}, 3개월 +${abs(c):.1f}) — 인플레 재확대 우려. "
            "정유·에너지·방산 수혜, 항공·화학·운수 원가 부담. "
            "한국 무역수지 악화 → 원화 약세 동반 가능성."
            if c > 3 else
            f"📉 유가 급락(${v:.1f}, 3개월 -${abs(c):.1f}) — 인플레 압력 완화, 소비 여력 개선. "
            "항공·화학·운송 원가 절감 수혜. "
            "단, 수요 급감 신호일 경우 경기침체 우려 동반 확인 필요."
            if c < -3 else
            f"➡️ 유가 안정(${v:.1f}) — 인플레 중립 구간. "
            "에너지 섹터 방향성 약화, 정유·화학 마진 현상 유지 전망."
        )),
        ("S&P500", "S&P 500", "", 0, lambda v, c: (
            f"{'📈' if c >= 0 else '📉'} 3개월 {_pct(v,c)} ({'반등세' if c > 0 else '조정세'}) — "
            "미국 증시 방향성은 한국 시장 선행 지표. "
            "강세 지속 시 국내 대형주(반도체·자동차) 외국인 수급 개선 기대. "
            "S&P 역대 최고가 부근 → 차익실현 물량·밸류에이션 부담 경계."
        )),
        ("NASDAQ", "NASDAQ", "", 0, lambda v, c: (
            f"{'📈' if c >= 0 else '📉'} 3개월 {_pct(v,c)} (기술주 {'강세' if c > 0 else '약세'}) — "
            "나스닥 방향성은 국내 반도체·IT·2차전지 동조화 경향 강함. "
            "나스닥 급등 시 갭업 후 차익실현 주의. "
            "AI·빅테크 실적·금리 민감도 병행 체크 권장."
        )),
        ("GOLD", "금 Gold", "$", 0, lambda v, c: (
            f"{'📈' if c >= 0 else '📉'} 3개월 {_pct(v,c)} — "
            + ("안전자산 선호 급증. 지정학 리스크·금융불안 신호. "
               "금 광산·귀금속 관련주 주목. 실질금리 하락 동반 시 추가 상승 여력."
               if c >= 0 else
               "위험선호 회복 신호. 주식·크립토 자금 유입 기대. "
               "단, 실질금리 상승 동반 시 추가 하락 가능성 → 안전자산 비중 재조정.")
        )),
        ("USDKRW", "원달러 환율", "₩", 0, lambda v, c: (
            f"{'📈' if c >= 0 else '📉'} 3개월 {_pct(v,c)} — "
            + (f"원화 약세({v:,.0f}원) — 삼성전자·현대차·LG에너지솔루션 등 수출 대형주 실적 수혜. "
               "수입 원자재 비용 상승으로 소재·에너지주 원가 압박. "
               "외국인 원화 자산 매력 감소 → 수급 주의."
               if c >= 0 else
               f"원화 강세({v:,.0f}원) — 외국인 한국 주식 순매수 유인 증가. "
               "수입 소비재·항공·여행주 원가 개선. "
               "반면 수출 대형주 환차손 우려 → 환헤지 여부 확인 필요.")
        )),
    ]

    rows_html = ""
    for i, (key, label, unit, dec, fn) in enumerate(specs):
        r = _r(key)
        if not r:
            continue
        val, chg = r
        bg       = BG_ROW if i % 2 == 0 else BG_ALT
        fmt      = f"{{:.{dec}f}}"
        val_str  = f"{unit}{fmt.format(val)}"
        chg_str  = fmt.format(abs(chg))
        chg_sym  = "▲" if chg >= 0 else "▼"
        chg_col  = C_UP if chg >= 0 else C_DN
        interp   = fn(val, chg)
        rows_html += (
            f'<tr style="background:{bg}">'
            f'<td style="padding:7px 11px;color:{C_KEY};font-weight:700;font-size:12px;'
            f'white-space:nowrap;border-bottom:1px solid {BORDER}">{label}</td>'
            f'<td style="padding:7px 11px;color:{C_VAL};font-size:12px;font-weight:700;'
            f'white-space:nowrap;border-bottom:1px solid {BORDER}">{val_str}</td>'
            f'<td style="padding:7px 11px;color:{chg_col};font-size:12px;font-weight:700;'
            f'white-space:nowrap;border-bottom:1px solid {BORDER}">{chg_sym} {chg_str}</td>'
            f'<td style="padding:7px 11px;color:{C_SUB};font-size:11px;line-height:1.6;'
            f'border-bottom:1px solid {BORDER};word-break:keep-all">{interp}</td>'
            f'</tr>'
        )

    if not rows_html:
        return "시장 지표 데이터를 불러오지 못했습니다."

    header = (
        f'<tr style="background:#1a3050">'
        f'<th style="padding:8px 11px;text-align:left;color:{C_KEY};font-size:11px;font-weight:700;border-bottom:2px solid #3a5070">지표</th>'
        f'<th style="padding:8px 11px;text-align:left;color:{C_KEY};font-size:11px;font-weight:700;border-bottom:2px solid #3a5070">현재값</th>'
        f'<th style="padding:8px 11px;text-align:left;color:{C_KEY};font-size:11px;font-weight:700;border-bottom:2px solid #3a5070">3개월변화</th>'
        f'<th style="padding:8px 11px;text-align:left;color:{C_KEY};font-size:11px;font-weight:700;border-bottom:2px solid #3a5070">해석</th>'
        f'</tr>'
    )
    summary = (
        f'<tr style="background:#162535">'
        f'<td colspan="4" style="padding:10px 11px;color:#81e084;font-size:12px;border-top:2px solid #3a6050">'
        f'📌 <strong>종합</strong>: 위 지표를 바탕으로 글로벌 매크로 흐름을 점검하고, 섹터별 수급 이슈와 연계해 투자 판단에 활용하세요.'
        f'</td></tr>'
    )
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;border-radius:6px;overflow:hidden">'
        f'{header}{rows_html}{summary}</table>'
    )
