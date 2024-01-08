import time
import pyupbit
import datetime
import requests

access = "TTAeLbSbGHRInxqAM8Hb4naKv9hTJASD6bfgTTia"
secret = "VSMpEKEExL8gtJS8xsMxXXRgYxUcq9kPrLUBC3OV"
myToken = "xoxb-6431908200277-6434852823026-0Q6cv3y1L5iM38yJRna1vsoW"

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )
    
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
    try:
        df = pyupbit.get_ohlcv(ticker, interval="day", count=5)
        ma5 = df['close'].rolling(5).mean().iloc[-1]
        return ma5
    except Exception as e:
        print(f"Error in get_ma5: {str(e)}")
        return None

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if 'currency' in b and b['currency'] == ticker:
            if 'balance' in b and b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]


upbit = pyupbit.Upbit(access, secret)

print("autotrade start")
# 시작 메세지 슬랙 전송
post_message(myToken, "#coin", "autotrade start")

btc_buy_limit = 5000000
eth_buy_limit = 5000000

while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-BTC")
        end_time = start_time + datetime.timedelta(days=1)
        
        if start_time < now < end_time - datetime.timedelta(seconds=10):
            btc_target_price = get_target_price("KRW-BTC", 0.5)
            eth_target_price = get_target_price("KRW-ETH", 0.5)
            btc_ma5 = get_ma5("KRW-BTC")
            eth_ma5 = get_ma5("KRW-ETH")
            btc_current_price = get_current_price("KRW-BTC")
            eth_current_price = get_current_price("KRW-ETH")
            
            if btc_target_price < btc_current_price and btc_ma5 < btc_current_price:
                krw = get_balance("KRW")
                if krw > 5000:
                    buy_amount = min(krw, btc_buy_limit)  
                    btc_to_buy = buy_amount / btc_current_price 
                    buy_result = upbit.buy_market_order("KRW-BTC", buy_amount * 0.9995)
                    post_message(myToken, "#coin", f"BTC buy : {buy_result}, Amount : {btc_to_buy}")
                    btc_buy_limit -= buy_amount  

            if eth_target_price < eth_current_price and eth_ma5 < eth_current_price:
                krw = get_balance("KRW")
                if krw > 5000:
                    buy_amount = min(krw, eth_buy_limit)  
                    eth_to_buy = buy_amount / eth_current_price  
                    buy_result = upbit.buy_market_order("KRW-ETH", buy_amount * 0.9995)
                    post_message(myToken, "#coin", f"ETH buy : {buy_result}, Amount : {eth_to_buy}")
                    eth_buy_limit -= buy_amount  
                    
        else:
            btc = get_balance("BTC")
            if btc > 0.00008:
                sell_result = upbit.sell_market_order("KRW-BTC", btc*0.9995)
                post_message(myToken, "#coin", "BTC sell : " + str(sell_result))
                
            eth = get_balance("ETH")
            if eth > 0.001:
                sell_result = upbit.sell_market_order("KRW-ETH", eth*0.9995)
                post_message(myToken, "#coin", "ETH sell : " + str(sell_result))
                
        time.sleep(1)
        
    except Exception as e:
        error_message = f"Error occurred: {str(e)}"
        print(error_message)
        post_message(myToken, "#coin", error_message)
        time.sleep(1)