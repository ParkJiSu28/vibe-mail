# 📊 vibe_mail — 일일 주식 브리핑 자동 발송

매일 오전 6시(KST), 전날 한국 주식시장이 열린 날에만 **거래대금 상위 30 종목 분석 이메일**을 자동으로 발송합니다.

## 주요 기능

- **거래대금 TOP 30** 종목 자동 수집 (KRX)
- **섹터별 트리맵** 차트 (거래대금 비중 + 대표 종목명)
- **52주 고가 근접 종목** 태그
- **투자자 동향** (개인 / 외국인 / 기관 순매수)
- **섹터별 최신 뉴스** (중복 제거 + 관련성 필터)
- **글로벌 시장 지표** 차트 3개월 (VIX, DXY, 금리, WTI, S&P500, NASDAQ, 금, 원달러)
- **시장 코멘트** 자동 생성

## 실행 조건

GitHub Actions가 전날(KST)이 한국 주식 개장일(`XKRX` 캘린더 기준)인 경우에만 이메일을 발송합니다.  
주말·공휴일에는 자동으로 건너뜁니다.

## GitHub 설정 방법

### 1. 저장소 Secrets 등록 (Settings → Secrets and variables → Actions)

| 구분 | 이름 | 값 |
|------|------|----|
| Secret | `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 (16자리) |
| Secret | `KRX_ID` | KRX 회원 아이디 |
| Secret | `KRX_PW` | KRX 회원 비밀번호 |
| Variable | `EMAIL_TO` | `수신자1@gmail.com,수신자2@gmail.com` |

> **Gmail 앱 비밀번호 발급**: Google 계정 → 보안 → 2단계 인증 활성화 후 → 앱 비밀번호 생성

### 2. 수신자 추가/변경

GitHub 저장소 → Settings → Secrets and variables → Actions → Variables 탭에서  
`EMAIL_TO` 값을 쉼표로 구분해 수정하면 코드 변경 없이 수신자를 관리할 수 있습니다.

```
qkrwltn28@gmail.com,chelseaj960126@gmail.com
```

### 3. 자동 실행 스케줄

```
cron: '0 21 * * 0-4'   # UTC 21:00 = KST 06:00 (월~금)
```

GitHub Actions 탭 → `일일 주식 브리핑` → `Run workflow` 버튼으로 즉시 테스트도 가능합니다.

## 로컬 실행 (개발/테스트)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# .env 파일 생성
echo "GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx" > .env
echo "KRX_ID=your_id" >> .env
echo "KRX_PW=your_pw" >> .env

python main.py
```

## 프로젝트 구조

```
vibe_mail/
├── main.py              # 메인 실행 파일 (스케줄 제어 포함)
├── config.py            # 설정 (발신자, 수신자, 기타 파라미터)
├── data_fetcher.py      # KRX·yfinance 데이터 수집
├── sector_mapper.py     # 34개 섹터 분류
├── news_scraper.py      # 섹터별 뉴스 수집 (5개 품질 규칙)
├── chart_builder.py     # 트리맵·시장차트 생성, 코멘트 생성
├── email_builder.py     # HTML 이메일 빌드
├── requirements.txt     # 패키지 의존성
└── .github/
    └── workflows/
        └── daily_briefing.yml   # GitHub Actions 워크플로우
```
