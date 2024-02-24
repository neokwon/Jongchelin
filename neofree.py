import time
import pyupbit
import datetime
import requests

access = ""
secret = ""
telegram_token = ""
telegram_chat_id = ""

def send_telegram_message(message):
    """Telegram 메시지 전송"""
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = {"chat_id": telegram_chat_id, "text": message}
    requests.post(url, data=data)

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_ma5(ticker):
    """5일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=5)
    ma15 = df['close'].rolling(5).mean().iloc[-1]
    return ma15

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

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

# 로그인
upbit = pyupbit.Upbit(access, secret)
send_telegram_message("자동매매 시작")

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        
        # 비트코인 매매
        btc_start_time = get_start_time("KRW-BTC")
        btc_end_time = btc_start_time + datetime.timedelta(days=1)
        if btc_start_time < now < btc_end_time - datetime.timedelta(seconds=10):
            btc_target_price = get_target_price("KRW-BTC", 0.5)
            btc_ma5 = get_ma5("KRW-BTC")
            btc_current_price = get_current_price("KRW-BTC")
            if btc_target_price < btc_current_price and btc_ma5 < btc_current_price:
                krw_balance = get_balance("KRW")
                btc_to_buy = krw_balance * 0.5 * 0.9995
                if krw_balance > 5000:
                    upbit.buy_market_order("KRW-BTC", btc_to_buy)
                    send_telegram_message("비트코인 매수 완료")
        else:
            btc_balance = get_balance("BTC")
            if btc_balance > 0.00008:
                upbit.sell_market_order("KRW-BTC", btc_balance*0.9995)
                send_telegram_message("비트코인 매도 완료")
        
        # 이더리움 매매
        eth_start_time = get_start_time("KRW-ETH")
        eth_end_time = eth_start_time + datetime.timedelta(days=1)
        if eth_start_time < now < eth_end_time - datetime.timedelta(seconds=10):
            eth_target_price = get_target_price("KRW-ETH", 0.5)
            eth_ma5 = get_ma5("KRW-ETH")
            eth_current_price = get_current_price("KRW-ETH")
            if eth_target_price < eth_current_price and eth_ma5 < eth_current_price:
                krw_balance = get_balance("KRW")
                eth_to_buy = krw_balance * 0.5 * 0.9995
                if krw_balance > 5000:
                    upbit.buy_market_order("KRW-ETH", eth_to_buy)
                    send_telegram_message("이더리움 매수 완료")
        else:
            eth_balance = get_balance("ETH")
            if eth_balance > 0.00008:
                upbit.sell_market_order("KRW-ETH", eth_balance*0.9995)
                send_telegram_message("이더리움 매도 완료")
        
        time.sleep(1)
    except Exception as e:
        print(e)
        time.sleep(1)
