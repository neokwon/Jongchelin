import time
import pyupbit
import datetime
import requests

access = ""
secret = ""
myToken = ""

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel, "text": text})

def get_target_price(ticker):
    df = pyupbit.get_ohlcv(ticker, interval='day', count=2)
    yesterday = df.iloc[-2]

    today_open = yesterday['close']
    yesterday_high = yesterday['high']
    yesterday_low = yesterday['low']
    target = today_open + (yesterday_high - yesterday_low) * 0.5
    return target

def buy_crypto_currency(ticker, limit_amount=10000000):
    krw_balance = upbit.get_balance("KRW")
    buy_limit = min(krw_balance, limit_amount)

    orderbook = pyupbit.get_orderbook(tickers=ticker)[0]
    sell_price = orderbook['orderbook_units'][0]['ask_price']
    unit = min(buy_limit / float(sell_price), krw_balance)
    
    if unit > 0:  # 매수할 수 있는 잔고가 있는 경우에만 주문 실행
        upbit.buy_market_order(ticker, unit)
        post_message(myToken, "#coin", f"매수 주문 완료: {ticker}, 가격: {sell_price}, 수량: {unit}")
    else:
        post_message(myToken, "#coin", "매수 제한에 걸려 매수 주문이 실행되지 않았습니다. 잔고: {krw_balance}")

def sell_crypto_currency(ticker):
    unit = upbit.get_balance(ticker)
    upbit.sell_market_order(ticker, unit)
    post_message(myToken, "#coin", f"매도 주문 완료: {ticker}, 수량: {unit}")

def get_yesterday_ma5(ticker):
    df = pyupbit.get_ohlcv(ticker, interval='day', count=6)
    close = df['close']
    ma = close.rolling(window=5).mean()
    return ma[-2]

upbit = pyupbit.Upbit(access, secret)

print("autotrade start")
# 시작 메세지 슬랙 전송
post_message(myToken, "#coin", "autotrade start")

now = datetime.datetime.now()
now_kst = now + datetime.timedelta(hours=9)

mid = datetime.datetime(now_kst.year, now_kst.month, now_kst.day) + datetime.timedelta(1)
ma5_btc = get_yesterday_ma5("KRW-BTC")
target_price_btc = get_target_price("KRW-BTC")

ma5_eth = get_yesterday_ma5("KRW-ETH")
target_price_eth = get_target_price("KRW-ETH")

while True:
    try:
        if mid < now < mid + datetime.timedelta(seconds=10): 
            target_price_btc = get_target_price("KRW-BTC")
            ma5_btc = get_yesterday_ma5("KRW-BTC")
            sell_crypto_currency("KRW-BTC")
            
            target_price_eth = get_target_price("KRW-ETH")
            ma5_eth = get_yesterday_ma5("KRW-ETH")
            sell_crypto_currency("KRW-ETH")
    
            mid = datetime.datetime(now_kst.year, now_kst.month, now_kst.day) + datetime.timedelta(1)
        
        current_price_btc = pyupbit.get_current_price("KRW-BTC")
        if (current_price_btc > target_price_btc) and (current_price_btc > ma5_btc):
            buy_crypto_currency("KRW-BTC", limit_amount=10000000)  # BTC 매수 제한: 10,000,000원
            

        current_price_eth = pyupbit.get_current_price("KRW-ETH")
        if (current_price_eth > target_price_eth) and (current_price_eth > ma5_eth):
            buy_crypto_currency("KRW-ETH", limit_amount=10000000)  # ETH 매수 제한: 10,000,000원
    except Exception as e:
        print("에러 발생:", e)
        
    time.sleep(1)