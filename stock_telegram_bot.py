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

DEFAULT_TARGET_TICKERS = [
    {
        "symbol": "SCHD",
        "name": "슈왑 미국 배당 ETF",
        "strategy_summary": "우량 배당성장주 지속 보유. 적립식 분할 매수 유효."
    },
    {
        "symbol": "QLD",
        "name": "프로스프레드 나스닥 2배",
        "strategy_summary": "나스닥 100 2배 추종. 단기 모멘텀 대응 유효하며 장기 보유 시 음의 복리 효과 주의."
    },
    {
        "symbol": "NU",
        "name": "누홀딩스",
        "strategy_summary": "멕시코 정식 은행 라이선스 취득으로 장기 펀더멘털 양호. 8월 13일 실적 발표 전 변동성 유의하며 실적 확인 후 관망 매수 권장."
    }
]

def extract_sheet_id(url_or_id):
    if not url_or_id:
        return None
    if "/d/" in url_or_id:
        parts = url_or_id.split("/d/")[1]
        sheet_id = parts.split("/")[0]
        return sheet_id
    return url_or_id.strip()

def normalize_ticker_symbol(symbol):
    symbol = symbol.strip().upper()
    if symbol.endswith(".KR"):
        symbol = symbol[:-3] + ".KS"
    elif len(symbol) == 6 and symbol.isdigit():
        symbol = symbol + ".KS"
    return symbol

def normalize_display_symbol(symbol):
    """표시용 종목코드 정돈 (441800.KS -> 441800)"""
    if symbol.endswith(".KS") or symbol.endswith(".KQ"):
        return symbol[:-3]
    return symbol

def fetch_tickers_from_google_sheet(sheet_url_or_id):
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
            raw_symbol = row[0].strip()
            
            if raw_symbol.upper() in ["SYMBOL", "TICKER", "티커", "종목코드", "종목"]:
                continue
            
            if not raw_symbol:
                continue

            symbol = normalize_ticker_symbol(raw_symbol)
            name = row[1].strip() if len(row) > 1 and row[1].strip() else symbol
            strategy = row[2].strip() if len(row) > 2 and row[2].strip() else "지정된 메모 없음"

            tickers.append({
                "symbol": symbol,
                "raw_symbol": raw_symbol,
                "display_symbol": normalize_display_symbol(symbol),
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
        
        if df.empty and symbol.endswith(".KS"):
            kq_symbol = symbol[:-3] + ".KQ"
            ticker = yf.Ticker(kq_symbol)
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
            "currency": "₩" if (symbol.endswith(".KS") or symbol.endswith(".KQ")) else "$",
            "news": news_items
        }
    except Exception as e:
        print(f"⚠️ {symbol} 데이터 조회 실패: {e}")
        return None

def get_display_width(text):
    """한글/한자 등 전각 문자를 2칸, 영문/숫자를 1칸으로 계산"""
    width = 0
    for ch in text:
        if ord(ch) > 0x7F:
            width += 2
        else:
            width += 1
    return width

def pad_str(text, target_width, align="left"):
    """한글 가독성을 고려한 문자열 패딩 함수"""
    curr_w = get_display_width(text)
    if curr_w >= target_width:
        res = ""
        w = 0
        for ch in text:
            cw = 2 if ord(ch) > 0x7F else 1
            if w + cw > target_width - 1:
                break
            res += ch
            w += cw
        return res + " " * (target_width - w)
    
    pad_len = target_width - curr_w
    if align == "right":
        return " " * pad_len + text
    return text + " " * pad_len

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
    
    msg = f"<b>📊 [주식 시가/종가 브리핑]</b>\n"
    msg += f"📅 기준일자: <code>{latest_date}</code>\n\n"

    # --- 1. 표(Table) 요약 브리핑 (종목코드, 종목명, 종가, 수익률) ---
    msg += "<b>📈 종목별 시세 요약 표</b>\n"
    msg += "<pre>"
    msg += "┌──────────┬───────────┬──────────┬──────────┐\n"
    msg += "│ 종목코드 │ 종목명    │ 종가     │ 수익률   │\n"
    msg += "├──────────┼───────────┼──────────┼──────────┤\n"

    for item in stock_results:
        disp_symbol = item.get('display_symbol', item['symbol'])
        name = item['name']
        data = item['data']

        code_cell = pad_str(disp_symbol[:8], 8, "left")
        name_cell = pad_str(name[:5], 9, "left")

        if data:
            curr = data.get("currency", "$")
            pct = data['change_pct']

            # 아이콘 규칙: 
            #   플러스(+) = 빨강 삼각형 (🔺)
            #   마이너스(-) = 선명한 파란색 동그라미 (🔵) -> Apple/안드로이드 모두 파란색 보장
            #   보합(0%) = 노랑 동그라미 (🟡)
            if pct > 0:
                icon = "🔺"
            elif pct < 0:
                icon = "🔵"
            else:
                icon = "🟡"

            if curr == "₩":
                price_str = f"₩{data['close']:,.0f}"
            else:
                price_str = f"${data['close']:.2f}"

            pct_str = f"{icon}{pct:+.2f}%"
            price_cell = pad_str(price_str, 8, "right")
            pct_cell = pad_str(pct_str, 8, "right")
        else:
            price_cell = pad_str("조회실패", 8, "right")
            pct_cell = pad_str("-", 8, "right")

        msg += f"│ {code_cell} │ {name_cell} │ {price_cell} │ {pct_cell} │\n"

    msg += "└──────────┴───────────┴──────────┴──────────┘\n"
    msg += "</pre>\n\n"

    # --- 2. 종목별 상세 카드 뷰 ---
    msg += "<b>📋 종목별 상세 현황 및 메모</b>\n\n"

    for item in stock_results:
        symbol = item['symbol']
        disp_symbol = item.get('display_symbol', symbol)
        name = item['name']
        data = item['data']
        strategy = item['strategy_summary']

        msg += f"▪️ <b>{name} ({disp_symbol})</b>\n"
        if data:
            curr = data.get("currency", "$")
            pct = data['change_pct']

            if pct > 0:
                icon = "🔺"
            elif pct < 0:
                icon = "🔵"
            else:
                icon = "🟡"

            if curr == "₩":
                msg += f"  • <b>종가:</b> ₩{data['close']:,.0f} ({icon} <b>{pct:+.2f}%</b>)\n"
                msg += f"  • <b>시가:</b> ₩{data['open']:,.0f} | <b>범위:</b> ₩{data['low']:,.0f} ~ ₩{data['high']:,.0f}\n"
            else:
                msg += f"  • <b>종가:</b> ${data['close']:.2f} ({icon} <b>{pct:+.2f}%</b>)\n"
                msg += f"  • <b>시가:</b> ${data['open']:.2f} | <b>범위:</b> ${data['low']:.2f} ~ ${data['high']:.2f}\n"
        else:
            msg += f"  • 주가 데이터를 조회할 수 없습니다.\n"

        if strategy and strategy != "지정된 메모 없음":
            msg += f"  💡 <b>메모:</b> {strategy}\n"

        if data and data.get('news'):
            msg += "  📰 <b>최근 뉴스:</b>\n"
            for news_title in data['news']:
                msg += f"    - {news_title}\n"

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

    target_tickers = []
    if GOOGLE_SHEET_URL:
        print(f"📖 구글 시트에서 종목 목록 조회 중... ({GOOGLE_SHEET_URL})")
        target_tickers = fetch_tickers_from_google_sheet(GOOGLE_SHEET_URL)
    
    if not target_tickers:
        print("📌 기본 설정된 종목 목록을 사용합니다.")
        target_tickers = DEFAULT_TARGET_TICKERS

    print(f"🔍 총 {len(target_tickers)}개 종목 데이터 조회 중...")
    results = []
    for item in target_tickers:
        data = get_stock_data(item['symbol'])
        results.append({
            "symbol": item['symbol'],
            "display_symbol": item.get('display_symbol', item['symbol']),
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
