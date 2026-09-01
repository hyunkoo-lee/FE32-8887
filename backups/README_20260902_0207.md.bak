# 📈 미국 주식(SCHD, QLD, NU) 텔레그램 일일 리포트 자동화 봇

미국 주식 시장 마감 후(SCHD, QLD, NU) 시가, 종가, 고가, 저가 및 주요 뉴스/매수·매도 방향성을 텔레그램으로 자동 전송해 주는 스크립트입니다.

---

## 🛠️ 1. 사전 준비 사항 (텔레그램 봇 생성)

1. **텔레그램 앱**에서 `@BotFather` 검색 후 대화 시작
2. `/newbot` 입력 후 안내에 따라 봇 이름 및 아이디 생성
3. 발급된 **HTTP API Token** 복사 (예: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`)
4. 텔레그램 검색창에서 생성한 봇 아이디를 검색하여 `/start` 메시지를 보내 대화 시작
5. 자신의 **Chat ID** 확인: 텔레그램 검색창에서 `@userinfobot` 검색 후 `/start`를 누르면 자신의 `Id` 숫자를 확인 가능

---

## ⚙️ 2. 로컬 실행 방법 (.env 설정)

1. 프로젝트 폴더의 `.env.example`을 복사하여 `.env` 파일 생성:
   ```bash
   cp .env.example .env
   ```
2. `.env` 파일 열고 자신의 토큰과 Chat ID 입력:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:자신의_봇_토큰
   TELEGRAM_CHAT_ID=123456789
   ```
3. 스크립트 실행:
   ```bash
   .venv/bin/python stock_telegram_bot.py
   ```

---

## ⏰ 3. 자동 실행 방법 (2가지 중 선택)

### 방법 A: GitHub Actions 사용 (추천 - PC 켜둘 필요 없음, 100% 무료)
1. 이 프로젝트를 GitHub 레포지토리에 커밋 & 푸시합니다.
2. GitHub 레포지토리 Settings -> `Secrets and variables` -> `Actions` 클릭
3. `New repository secret` 버튼을 눌러 다음 2개 등록:
   - `TELEGRAM_BOT_TOKEN`: 봇 토큰 값
   - `TELEGRAM_CHAT_ID`: 텔레그램 Chat ID 값
4. 매일 미국 장 마감 후(한국시간 평일 오전 6시)에 텔레그램 메시지가 자동으로 발송됩니다.

### 방법 B: Mac crontab 사용 (내 컴퓨터에서 자동 실행)
터미널에서 `crontab -e` 명령어를 실행하고 아래 줄을 추가합니다 (평일 오전 6시 실행예시):
```bash
0 6 * * 1-5 /Users/orangeheim/Library/CloudStorage/GoogleDrive-qntjd201@gmail.com/내\ 드라이브/workspace/scheduleTask/.venv/bin/python /Users/orangeheim/Library/CloudStorage/GoogleDrive-qntjd201@gmail.com/내\ 드라이브/workspace/scheduleTask/stock_telegram_bot.py
```
