import time
import pyupbit
import datetime
import requests
import numpy as np
import talib

access = ""
secret = ""
bot_token = ""
chat_id = ""

def send_message(text):
    """Telegram 메시지 전송"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {"chat_id": chat_id, "text": text}
    requests.post(url, params=params)

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_rsi(ticker, interval, period):
    """RSI 계산"""
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=period+1)
    close = df['close']
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
# 시작 메세지 텔레그램 전송
send_message("Auto trade started.")

while True:
    try:
        prev_rsi_10m = get_rsi("KRW-ETH", "minute10", 14)  # 이전 봉의 RSI 값
        current_rsi_10m = get_rsi("KRW-ETH", "minute10", 14)  # 현재 봉의 RSI 값

        if prev_rsi_10m < 70 and current_rsi_10m >= 70 and macd_10m > signal_10m:
            krw = get_balance("KRW")
            if krw > 5000:
                buy_result = upbit.buy_market_order("KRW-ETH", krw*0.9995)
                send_message(f"ETH buy : {buy_result}")

        elif prev_rsi_10m > 70 and current_rsi_10m <= 70:
            eth = get_balance("ETH")
            if eth > 0.001:
                sell_result = upbit.sell_market_order("KRW-ETH", eth*0.9995)
                send_message(f"ETH sell : {sell_result}")

        time.sleep(10)  # 매 10초마다 검사
    except Exception as e:
        print(e)
        send_message(str(e))
        time.sleep(1)
