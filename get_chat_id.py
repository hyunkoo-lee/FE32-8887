import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8817351065:AAGo6DNWThSDMu_TSuoptxvLAzFXcnrsexM")

print("🤖 텔레그램 봇 연결 준비 중...")
print(f"👉 텔레그램 앱에서 봇 대화창 열기: https://t.me/gem_trade_bot")
print("👉 봇 대화창 하단의 [시작] (또는 /start) 버튼을 눌러주세요.\n")
print("⏳ 메시지를 기다리는 중입니다 (최대 60초)...")

start_time = time.time()
found_chat_id = None

while time.time() - start_time < 60:
    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates").json()
    if res.get("ok") and res.get("result"):
        for update in res["result"]:
            if "message" in update:
                chat = update["message"]["chat"]
                found_chat_id = str(chat["id"])
                user_name = chat.get("first_name", "사용자")
                print(f"✅ [{user_name}] 님의 Chat ID를 찾았습니다: {found_chat_id}")
                break
    if found_chat_id:
        break
    time.sleep(2)

if found_chat_id:
    # .env 파일 업데이트
    env_content = f"TELEGRAM_BOT_TOKEN={BOT_TOKEN}\nTELEGRAM_CHAT_ID={found_chat_id}\n"
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    print("📝 .env 파일에 TELEGRAM_CHAT_ID가 자동 저장되었습니다.")

    # 테스트 메시지 전송
    test_msg = "🎉 <b>gem-trade 봇 연동 성공!</b>\n\n앞으로 미국 주식(SCHD, QLD, NU) 리포트가 이 텔레그램 대화창으로 발송됩니다."
    send_res = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": found_chat_id, "text": test_msg, "parse_mode": "HTML"}
    ).json()

    if send_res.get("ok"):
        print("🚀 텔레그램 테스트 메시지가 성공적으로 발송되었습니다!")
    else:
        print(f"⚠️ 메시지 발송 실패: {send_send_res}")
else:
    print("⏰ 시간 초과: 텔레그램에서 봇 대화창을 열고 /start 를 누른 후 다시 실행해 보세요.")
