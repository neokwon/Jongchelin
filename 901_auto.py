import aiohttp
import asyncio
import websockets
import pybithumb
import pyupbit
import json
import jwt
import uuid
import time
import hashlib
import requests
from urllib.parse import urlencode

def load_keys():
    with open('keys2.json', 'r') as f:
        keys = json.load(f)
    return keys

def create_upbit_token(access_key, secret_key, body):
    nonce = str(uuid.uuid4())
    query = urlencode(body).encode()
    m = hashlib.sha512()
    m.update(query)
    query_hash = m.hexdigest()
    payload = {
        'access_key': access_key,
        'nonce': nonce,
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512'
    }
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return f'Bearer {token}'

def create_bithumb_token(access_key, secret_key, params):
    nonce = str(uuid.uuid4())
    query = urlencode(params).encode()
    m = hashlib.sha512()
    m.update(query)
    query_hash = m.hexdigest()
    payload = {
        'access_key': access_key,
        'nonce': nonce,
        'timestamp': round(time.time() * 1000),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512'
    }
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return f'Bearer {token}'

class WebsocketThread:
    def __init__(self, url, subscribe_msg, on_data_received):
        self.url = url
        self.subscribe_msg = subscribe_msg
        self.is_connected = False
        self.on_data_received = on_data_received

    async def websocket_connection(self):
        while True:
            try:
                async with websockets.connect(self.url) as websocket:
                    self.is_connected = True
                    await websocket.send(self.subscribe_msg)
                    while True:
                        data = await websocket.recv()
                        self.on_data_received(json.loads(data))
            except websockets.exceptions.ConnectionClosed:
                self.is_connected = False
                print("웹소켓 연결이 끊겼습니다. 재연결을 시도합니다.")
                await asyncio.sleep(10)
            except Exception as e:
                print(f"웹소켓 연결 중 오류 발생: {e}")
                await asyncio.sleep(10)

def get_upbit_balance(upbit):
    try:
        krw_balance = upbit.get_balance("KRW")
        xrp_balance = upbit.get_balance("XRP")
        if krw_balance is None or xrp_balance is None:
            raise ValueError("Failed to fetch Upbit balances, received None.")
        return float(krw_balance), float(xrp_balance)
    except Exception as e:
        print(f"Failed to fetch Upbit balance: {e}")
        return 0, 0


def get_bithumb_balance(access_key, secret_key):
    try:
        apiUrl = 'https://api.bithumb.com'
        nonce = str(uuid.uuid4())
        timestamp = round(time.time() * 1000)
        payload = {
            'access_key': access_key,
            'nonce': nonce,
            'timestamp': timestamp
        }
        jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
        authorization_token = f'Bearer {jwt_token}'
        headers = {
            'Authorization': authorization_token
        }
        response = requests.get(apiUrl + '/v1/accounts', headers=headers)

        if response.status_code != 200:
            raise ValueError(f"Failed to fetch Bithumb balances, status code: {response.status_code}")

        response_data = response.json()
        # 원화(KRW) 및 XRP 잔고 추출
        krw_balance = next((item['balance'] for item in response_data if item['currency'] == 'KRW'), 0)
        xrp_balance = next((item['balance'] for item in response_data if item['currency'] == 'XRP'), 0)

        return float(krw_balance), float(xrp_balance)
    except Exception as e:
        print(f"Failed to fetch Bithumb balance: {e}")
        raise

class TradingLogic:
    def __init__(self, upbit_keys, bithumb_keys):
        keys = load_keys()
        self.upbit_access_key = keys['upbit']['access_key']
        self.upbit_secret_key = keys['upbit']['secret_key']
        self.bithumb_access_key = keys['bithumb']['access_key']
        self.bithumb_secret_key = keys['bithumb']['secret_key']

        self.telegram_bot_token = keys['telegram']['bot_token']
        self.telegram_chat_id = keys['telegram']['chat_id']

        self.session = None
        self.upbit = pyupbit.Upbit(self.upbit_access_key, self.upbit_secret_key)
        self.bithumb = pybithumb.Bithumb(self.bithumb_access_key, self.bithumb_secret_key)

        self.upbit_bid = 0.0
        self.upbit_ask = 0.0
        self.bithumb_ask = 0.0
        self.bithumb_bid = 0.0
        # self.threshold3 = 200
        # self.threshold4 = 500
        # self.threshold5 = 300000
        # self.threshold6 = 1000

        self.running = True
        self.trading_active = False

    async def init_session(self):
        self.session = await aiohttp.ClientSession().__aenter__()

    async def close_session(self):
        if self.session:
            await self.session.__aexit__(None, None, None)

    async def start_trading(self):
        await self.init_session()
        self.trading_active = True
        try:
            print('주문이 실행되었습니다.')
            await self.execute_trading_logic()
        except Exception as e:
            print(f"실행 중 오류 발생: {e}")
            self.trading_active = False

    def stop_trading(self):
        self.trading_active = False
        self.running = False  # 추가: 루프를 종료하기 위해 running을 False로 설정
        print("TradingLogic 내에서 trading_active 상태 변경됨")

    def set_thresholds(self, threshold1, threshold2):
        self.threshold1 = threshold1
        self.threshold2 = threshold2

    def get_thresholds(self):
        return self.threshold1, self.threshold2

    def set_additional_thresholds(self, threshold3, threshold4, threshold5, threshold6):
        self.threshold3 = threshold3
        self.threshold4 = threshold4
        self.threshold5 = threshold5
        self.threshold6 = threshold6

    def get_additional_thresholds(self):
        return self.threshold3, self.threshold4, self.threshold5, self.threshold6

    def update_upbit_data(self, data):
        try:
            if data['type'] == 'orderbook':
                best_ask = data['orderbook_units'][0]['ask_price']
                best_ask_size = data['orderbook_units'][0]['ask_size']
                best_bid = data['orderbook_units'][0]['bid_price']
                best_bid_size = data['orderbook_units'][0]['bid_size']
                self.upbit_ask = float(best_ask)
                self.upbit_ask_size = float(best_ask_size)
                self.upbit_bid = float(best_bid)
                self.upbit_bid_size = float(best_bid_size)
        except KeyError as e:
            print(f"Upbit 데이터 처리 중 오류 발생: {e}")

    def update_bithumb_data(self, data):
        try:
            if data.get('type') == 'orderbooksnapshot':
                content = data.get('content', {})
                asks = content.get('asks', [])[:1]
                bids = content.get('bids', [])[:1]
                for ask, bid in zip(asks, bids):
                    ask_price, ask_quantity = ask
                    bid_price, bid_quantity = bid
                    self.bithumb_ask = float(ask_price)
                    self.bithumb_ask_quantity = float(ask_quantity)
                    self.bithumb_bid = float(bid_price)
                    self.bithumb_bid_quantity = float(bid_quantity)
        except KeyError as e:
            print(f"Bithumb 데이터 처리 중 오류 발생: {e}")

    def calculate_arbitrage(self):
        if self.upbit_ask == 0 or self.bithumb_ask == 0:
            return 0, 0

        bisellupbuy = ((self.bithumb_bid) - (self.upbit_ask * 1.0005)) / (self.upbit_ask * 1.0005) * 100
        upsellbibuy = ((self.upbit_bid * 0.9995) - (self.bithumb_ask)) / (self.bithumb_ask) * 100
        return bisellupbuy, upsellbibuy

    def update_balances(self):
        upbit_krw_balance, upbit_xrp_balance = get_upbit_balance(self.upbit)
        bithumb_krw_balance, bithumb_xrp_balance = get_bithumb_balance(self.bithumb_access_key, self.bithumb_secret_key)
        return upbit_krw_balance, upbit_xrp_balance, bithumb_krw_balance, bithumb_xrp_balance

    async def send_telegram_message(self, message):
        try:
            url = f'https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage'
            data = {'chat_id': self.telegram_chat_id, 'text': message}
            async with self.session.post(url, data=data) as response:
                if response.status != 200:
                    resp_text = await response.text()
                    print(f"Failed to send Telegram message: {resp_text}")
        except Exception as e:
            print(f"Error sending Telegram message: {e}")

    async def check_balances_and_stop(self):
        upbit_krw, upbit_xrp, bithumb_krw, bithumb_xrp = self.update_balances()
        threshold3, threshold4, threshold5, threshold6 = self.get_additional_thresholds()
        if upbit_xrp < threshold4 or bithumb_xrp < threshold4:
            self.stop_trading()
            message = "코인 잔량 부족으로 매매 중단."
            print(message)
            await self.send_telegram_message(message)
            return True
        if upbit_krw < threshold5 or bithumb_krw < threshold5:
            self.stop_trading()
            message = "원화 잔량 부족으로 매매 중단."
            print(message)
            await self.send_telegram_message(message)
            return True
        return False

    async def execute_trading_logic(self):
        try:
            # 최초 잔고 확인
            if await self.check_balances_and_stop():
                return False

            threshold1, threshold2 = self.get_thresholds()
            threshold3, threshold4, threshold5, threshold6 = self.get_additional_thresholds()
            print(f"Thresholds: {threshold1}, {threshold2}, {threshold3}, {threshold4}, {threshold5}, {threshold6}")

            upbit_krw, upbit_xrp, bithumb_krw, bithumb_xrp = self.update_balances()
            print(f"업비트 KRW 잔고: {upbit_krw}, XRP 잔고: {upbit_xrp}")
            print(f"빗썸 KRW 잔고: {bithumb_krw}, XRP 잔고: {bithumb_xrp}")

            start_message = (
                "매매를 시작합니다.\n\n"
                f"업비트 KRW 잔고: {upbit_krw}\n"
                f"업비트 XRP 잔고: {upbit_xrp}\n"
                f"빗썸 KRW 잔고: {bithumb_krw}\n"
                f"빗썸 XRP 잔고: {bithumb_xrp}"
            )
            await self.send_telegram_message(start_message)

            future = self.process_orders(threshold1, threshold2, threshold3)
            await future

        except Exception as e:
            print(f"실행 중 오류 발생: {e}")

    async def compare_bisellupbuy(self, bisellupbuy, threshold1, threshold6):
        if bisellupbuy >= threshold1 and self.bithumb_bid_quantity >= threshold6 and self.upbit_ask_size >= threshold6:
            await self.sell_bithumb_buy_upbit()

    async def compare_upsellbibuy(self, upsellbibuy, threshold2, threshold6):
        if upsellbibuy >= threshold2 and self.upbit_bid_size >= threshold6 and self.bithumb_ask_quantity >= threshold6:
            await self.sell_upbit_buy_bithumb()

    async def process_orders(self, threshold1, threshold2, threshold3):
        print("process_orders 호출완료")
        while self.running:
            bisellupbuy, upsellbibuy = self.calculate_arbitrage()

            task1 = self.compare_bisellupbuy(bisellupbuy, threshold1, threshold3)
            task2 = self.compare_upsellbibuy(upsellbibuy, threshold2, threshold3)

            await asyncio.gather(task1, task2)
            await asyncio.sleep(0.05)


    async def sell_bithumb_buy_upbit(self):
        try:

            bithumb_sell_future = self.bithumb_sell_limit_order("KRW-XRP", self.threshold3)
            upbit_buy_future = self.upbit_buy_limit_order("KRW-XRP", self.threshold3)

            await asyncio.gather(upbit_buy_future, bithumb_sell_future)

            if await self.check_balances_and_stop():
                return

        except Exception as e:
            print(f"Error during market sell at Bithumb and buy at Upbit: {e}")

    async def sell_upbit_buy_bithumb(self):
        try:

            upbit_sell_future = self.upbit_sell_limit_order("KRW-XRP", self.threshold3)
            bithumb_buy_future = self.bithumb_buy_limit_order("KRW-XRP", self.threshold3)

            await asyncio.gather(upbit_sell_future, bithumb_buy_future)

            if await self.check_balances_and_stop():
                return

        except Exception as e:
            print(f"Error during buy at Bithumb and sell at Upbit: {e}")

    async def upbit_buy_limit_order(self, ticker, quantity):
        body = {
            "market": ticker,
            "side": "bid",
            "volume": str(quantity),
            "price": str(self.upbit_ask),
            "ord_type": "limit"
        }
        authorization_token = create_upbit_token(self.upbit_access_key, self.upbit_secret_key, body)
        headers = {
            "Authorization": authorization_token,
            "Content-Type": "application/json"
        }
        url = 'https://api.upbit.com/v1/orders'
        response = await self.session.post(url, headers=headers, json=body)
        return await response.json()

    async def upbit_sell_limit_order(self, ticker, quantity):
        body = {
            "market": ticker,
            "side": "ask",
            "volume": str(quantity),
            "price": str(self.upbit_bid),
            "ord_type": "limit"
        }
        authorization_token = create_upbit_token(self.upbit_access_key, self.upbit_secret_key, body)
        headers = {
            "Authorization": authorization_token,
            "Content-Type": "application/json"
        }
        url = 'https://api.upbit.com/v1/orders'
        response = await self.session.post(url, headers=headers, json=body)
        return await response.json()

    async def bithumb_sell_limit_order(self, ticker, quantity):
        params = {
            "market": ticker,
            "side": "ask",
            "volume": str(quantity),
            "price": str(self.bithumb_bid),
            "ord_type": "limit"
        }
        authorization_token = create_bithumb_token(self.bithumb_access_key, self.bithumb_secret_key, params)
        headers = {
            'Authorization': authorization_token,
            'Content-Type': 'application/json'
        }
        url = 'https://api.bithumb.com/v1/orders'
        response = await self.session.post(url, headers=headers, json=params)
        return await response.json()

    async def bithumb_buy_limit_order(self, ticker, quantity):
        params = {
            "market": ticker,
            "side": "bid",
            "volume": str(quantity),
            "price": str(self.bithumb_ask),
            "ord_type": "limit"
        }
        authorization_token = create_bithumb_token(self.bithumb_access_key, self.bithumb_secret_key, params)
        headers = {
            'Authorization': authorization_token,
            'Content-Type': 'application/json'
        }
        url = 'https://api.bithumb.com/v1/orders'
        response = await self.session.post(url, headers=headers, json=params)
        return await response.json()

async def main():
    keys = load_keys()
    trading_logic = TradingLogic(keys['upbit'], keys['bithumb'])

    # 임계값 설정
    trading_logic.set_thresholds(0.07, 0.07)
    trading_logic.set_additional_thresholds(200, 500, 300000, 1000)

    # 웹소켓 초기화
    upbit_ws = WebsocketThread(
        "wss://api.upbit.com/websocket/v1",
        json.dumps([{"ticket":"test"},{"type": "orderbook", "codes": ["KRW-XRP"], "isOnlyRealtime": True}]),
        trading_logic.update_upbit_data
    )

    bithumb_ws = WebsocketThread(
        "wss://pubwss.bithumb.com/pub/ws",
        json.dumps({"type": "orderbooksnapshot", "symbols": ["XRP_KRW"]}),
        trading_logic.update_bithumb_data
    )

    await asyncio.gather(
        upbit_ws.websocket_connection(),
        bithumb_ws.websocket_connection(),
        trading_logic.start_trading()
    )

if __name__ == "__main__":
    asyncio.run(main())
