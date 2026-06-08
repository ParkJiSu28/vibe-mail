"""
=============================================================
  vibe_mail 설정 파일
=============================================================

【수신자 관리 가이드】
─────────────────────────────────────────────────────────────
EMAIL_TO 리스트에 이메일 주소를 추가/삭제하면 됩니다.

  예시:
    EMAIL_TO = [
        "qkrwltn28@gmail.com",      # 본인 (메인 수신자)
        "friend@gmail.com",          # 추가 수신자
        "colleague@company.com",     # 회사 동료
    ]

  ✅ 한 명만 받을 때:
    EMAIL_TO = ["qkrwltn28@gmail.com"]

  ✅ 여러 명에게 한 번에 보낼 때:
    EMAIL_TO = [
        "qkrwltn28@gmail.com",
        "another@example.com",
    ]

  ⚠️  주의사항:
    - 각 주소는 큰따옴표(" ")로 감싸고 쉼표(,)로 구분하세요.
    - Gmail 앱 비밀번호(GMAIL_APP_PASSWORD)는 .env 파일에 저장하세요.
      → 2단계 인증 후 Google 계정 > 보안 > 앱 비밀번호에서 생성

─────────────────────────────────────────────────────────────
【발송 시간 / 스케줄 관리】
  cron은 매일 오전 6시(KST)에 실행됩니다.
  main.py가 자동으로 한국/미국 거래일이 아닌 날은 건너뜁니다.

  crontab 수정: crontab -e
    현재 설정:  0 6 * * * /Users/parkjisu/Desktop/vibe_mail/run_daily.sh

─────────────────────────────────────────────────────────────
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── 발신자 계정 (Gmail) ──────────────────────────────────────────────
EMAIL_USER = "qkrwltn28@gmail.com"

# Gmail 앱 비밀번호: .env 파일에 GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx 형태로 저장
EMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# ── 수신자 목록 ─────────────────────────────────────────────────────
# GitHub Actions: EMAIL_TO 환경변수(Variables)에 쉼표 구분 주소 설정 → 우선 사용
# 로컬 실행: 환경변수 없으면 아래 하드코딩 리스트 사용
_env_to = os.getenv("EMAIL_TO", "")
EMAIL_TO = [e.strip() for e in _env_to.split(",") if e.strip()] or [
    "qkrwltn28@gmail.com",
    "chelseaj960126@gmail.com",
    "dmstn7185@naver.com",
    "barabajuo@hanmail.net",
    "totori1905@gmail.com",
]

# ── 기타 설정 ────────────────────────────────────────────────────────
TOP_N_STOCKS          = 30     # 거래대금 상위 N개 종목
NEWS_COUNT_DEFAULT    = 3      # 섹터별 기본 뉴스 수
NEWS_COUNT_TOP_SECTOR = 5      # 거래대금 1위 섹터 뉴스 수
HIGH_APPROACH_PCT     = 0.05   # 52주 신고가 '근접' 기준 (5% 이내)
