import time
from binance.client import Client
from binance.websockets import BinanceSocketManager

from modules import utils

try:
  key, secret = utils.loadJSON('config/binance.json').values()
  client      = Client(key, secret)
except:
  pass

def createSocketManager():
  return BinanceSocketManager(client)

def request(method, args=()):
  method = client.__getattribute__(method)

  while True:
    try:
      if type(args) is tuple:
        return method(*args)
      elif type(args) is dict:
        return method(**args)
    except Exception as e:
      print(e)
      time.sleep(1)
      pass

def getBalance(asset):
  try:
    return float(request('get_asset_balance', { 'asset': asset })['free'])
  except:
    print(f'Quote {asset} invalid.')
    exit(1)

def getCandles(symbol, timeframe):
  return request('get_klines', { 'symbol': symbol, 'interval': timeframe })

def placeOrder(symbol, lotSize, side, baseQuantity):
  return request(f'order_market_{side}', { 'symbol': symbol, 'quantity': utils.formatFloat(baseQuantity, lotSize) })