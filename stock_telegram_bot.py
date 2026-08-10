import os
import sys
import csv
import io
import datetime
import requests
import yfinance as yf
from dotenv import load_dotenv

# .env 파일 로드 (로컬 실행 시)
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL")

# 구글 시트 연동이 없을 때 사용하는 기본 종목 리스트
DEFAULT_TARGET_TICKERS = [
    {
        "symbol": "SCHD",
        "name": "Schwab U.S. Dividend Equity ETF",
        "strategy_summary": "우량 배당성장주 지속 보유. 적립식 분할 매수 유효."
    },
    {
        "symbol": "QLD",
        "name": "ProShares Ultra QQQ (2x Leverage)",
        "strategy_summary": "나스닥 100 2배 추종. 단기 모멘텀 대응 유효하며 장기 보유 시 음의 복리 효과 주의."
    },
    {
        "symbol": "NU",
        "name": "Nu Holdings Ltd.",
        "strategy_summary": "멕시코 정식 은행 라이선스 취득으로 장기 펀더멘털 양호. 8월 13일 실적 발표 전 변동성 유의하며 실적 확인 후 관망 매수 권장."
    }
]

def extract_sheet_id(url_or_id):
    """구글 시트 URL에서 Sheet ID 추출"""
    if not url_or_id:
        return None
    if "/d/" in url_or_id:
        parts = url_or_id.split("/d/")[1]
        sheet_id = parts.split("/")[0]
        return sheet_id
    return url_or_id.strip()

def fetch_tickers_from_google_sheet(sheet_url_or_id):
    """구글 시트 CSV 공개 링크를 통해 종목 및 메모 수집"""
    sheet_id = extract_sheet_id(sheet_url_or_id)
    if not sheet_id:
        return []

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        res = requests.get(csv_url, timeout=10)
        if res.status_code != 200:
            print(f"⚠️ 구글 시트 불러오기 실패 (HTTP {res.status_code})")
            return []

        csv_text = res.content.decode('utf-8')
        reader = csv.reader(io.StringIO(csv_text))
        
        tickers = []
        for row in reader:
            if not row or len(row) == 0:
                continue
            symbol = row[0].strip().upper()
            
            # 헤더 행 스킵 (Symbol, 티커, 종목코드 등)
            if symbol in ["SYMBOL", "TICKER", "티커", "종목코드", "종목"]:
                continue
            
            if not symbol:
                continue

            name = row[1].strip() if len(row) > 1 and row[1].strip() else symbol
            strategy = row[2].strip() if len(row) > 2 and row[2].strip() else "지정된 메모 없음"

            tickers.append({
                "symbol": symbol,
                "name": name,
                "strategy_summary": strategy
            })

        print(f"📊 구글 시트에서 총 {len(tickers)}개 종목을 가져왔습니다.")
        return tickers
    except Exception as e:
        print(f"⚠️ 구글 시트 읽기 중 오류 발생: {e}")
        return []

def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5d")
        if df.empty:
            return None
        
        latest_row = df.iloc[-1]
        date_str = latest_row.name.strftime('%Y-%m-%d')
        
        open_price = float(latest_row['Open'])
        high_price = float(latest_row['High'])
        low_price = float(latest_row['Low'])
        close_price = float(latest_row['Close'])
        volume = int(latest_row['Volume'])
        
        prev_close = float(df.iloc[-2]['Close']) if len(df) > 1 else close_price
        change_pct = ((close_price - prev_close) / prev_close) * 100

        # 최근 뉴스 가져오기 (최대 2건)
        news_items = []
        try:
            raw_news = ticker.news
            if raw_news:
                for item in raw_news[:2]:
                    title = item.get("title") or item.get("content", {}).get("title")
                    if title:
                        news_items.append(title)
        except Exception:
            pass

        return {
            "date": date_str,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "change_pct": change_pct,
            "volume": volume,
            "news": news_items
        }
    except Exception as e:
        print(f"⚠️ {symbol} 데이터 조회 실패: {e}")
        return None

def format_telegram_message(stock_results):
    if not stock_results:
        return "데이터를 불러오는 데 실패했습니다."

    latest_date = None
    for r in stock_results:
        if r.get('data'):
            latest_date = r['data']['date']
            break
    if not latest_date:
        latest_date = datetime.date.today().strftime('%Y-%m-%d')
    
    msg = f"<b>📊 [미국 주식 시가/종가 및 방향성 리포트]</b>\n"
    msg += f"📅 기준일자: <code>{latest_date}</code>\n\n"

    for item in stock_results:
        symbol = item['symbol']
        name = item['name']
        data = item['data']
        strategy = item['strategy_summary']

        msg += f"<b>🔹 {symbol} ({name})</b>\n"
        if data:
            change_emoji = "🔺" if data['change_pct'] >= 0 else "🔻"
            msg += f"• <b>시가(Open):</b> ${data['open']:.2f}\n"
            msg += f"• <b>종가(Close):</b> ${data['close']:.2f} ({change_emoji} {data['change_pct']:+.2f}%)\n"
            msg += f"• <b>당일 변동:</b> ${data['low']:.2f} ~ ${data['high']:.2f}\n"
        else:
            msg += f"• 주가 데이터를 조회할 수 없습니다.\n"

        if strategy and strategy != "지정된 메모 없음":
            msg += f"💡 <b>메모/전략:</b> {strategy}\n"

        if data and data.get('news'):
            msg += "📰 <b>최근 주요 헤드라인:</b>\n"
            for news_title in data['news']:
                msg += f"  - {news_title}\n"

        msg += "\n"

    msg += "⚠️ <i>본 리포트는 자동 생성되었으며 투자 참고용입니다.</i>"
    return msg

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    response = requests.post(url, data=payload)
    return response.json()

def main():
    is_dry_run = "--dry-run" in sys.argv or "--test" in sys.argv

    if not is_dry_run and (not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID):
        print("❌ 오류: TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 값이 설정되지 않았습니다.")
        sys.exit(1)

    # 구글 시트 연동 여부 확인
    target_tickers = []
    if GOOGLE_SHEET_URL:
        print(f"📖 구글 시트에서 종목 목록 조회 중... ({GOOGLE_SHEET_URL})")
        target_tickers = fetch_tickers_from_google_sheet(GOOGLE_SHEET_URL)
    
    if not target_tickers:
        print("📌 기본 설정된 종목 목록(SCHD, QLD, NU)을 사용합니다.")
        target_tickers = DEFAULT_TARGET_TICKERS

    print(f"🔍 총 {len(target_tickers)}개 종목 데이터 조회 중...")
    results = []
    for item in target_tickers:
        data = get_stock_data(item['symbol'])
        results.append({
            "symbol": item['symbol'],
            "name": item['name'],
            "strategy_summary": item['strategy_summary'],
            "data": data
        })

    report = format_telegram_message(results)
    print("\n--- 생성된 리포트 ---")
    print(report)
    print("-------------------\n")

    if is_dry_run:
        print("🧪 Dry-run 모드입니다. 텔레그램 메시지를 실제로 전송하지 않았습니다.")
        return

    print("🚀 텔레그램 메세지 전송 중...")
    res = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, report)
    if res.get("ok"):
        print("✅ 텔레그램 전송 성공!")
    else:
        print(f"❌ 텔레그램 전송 실패: {res}")

if __name__ == "__main__":
    main()
