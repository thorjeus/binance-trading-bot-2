import time

from modules import binance
from modules import utils

from bot import strategies

class TradingBot:
  def __init__(self, config):
    # User config
    stablecoins, riskManagement, fee, quote, marketNum, timeframes, strategies = config.values()

    self.stablecoins    = stablecoins
    self.riskManagement = riskManagement
    self.fee            = fee
    self.quote          = quote
    self.marketNum      = marketNum
    self.timeframes     = timeframes
    self.strategies     = strategies

    # Bot properties
    self.lastTrades      = {}
    self.mktsCurrTrading = []
    self.lotsInUse       = 0
    self.candles         = {}
    self.filters         = {}
    self.socketManager   = binance.createSocketManager()

    utils.clearTerminal()
  
  def startTrading(self):
    self.socketManager.close()

    print('[TRADING BOT] Loading symbols info...')
    self.symbolsInfo = binance.request('get_exchange_info')['symbols']
    
    for info in self.symbolsInfo:
      if info['quoteAsset'] == self.quote:
        self.lastTrades[info['symbol']] = 0
        for fltr in info['filters']:
          if fltr['filterType'] == 'LOT_SIZE':
            self.filters[info['symbol']] = fltr['stepSize']
          elif fltr['filterType'] == 'MIN_NOTIONAL':
            self.minNotional = float(fltr['minNotional'])

    self.setLotSize()
    
    print(f'[TRADING BOT] Loading candles from {self.marketNum * len(self.timeframes)} markets... (This may take few moments)')
    self.setTradingSymbols(self.marketNum)
    for symbol in self.symbols:
      for tf in self.timeframes:
        self.candles[f'{symbol}_{tf}'] = [list(map(lambda x: float(x), candle)) for candle in binance.getCandles(symbol, tf)]
        time.sleep(1)

    streams = []
    for x in self.timeframes:
      streams += [f'{y.lower()}@kline_{x}' for y in self.symbols]

    self.socketManager = binance.createSocketManager()
    self.socketManager.start_multiplex_socket(streams=streams, callback=self.socketCallback)
    print('[TRADING BOT] Connected to websockets, trading started.')
    self.socketManager.run()

  def setTradingSymbols(self, length):
    symbols = [x['symbol'] for x in self.symbolsInfo if (
      x['baseAsset'] not in self.stablecoins and
      x['quoteAsset'] == self.quote and
      x['status'] == 'TRADING'
    )]
    symbols = [[x['symbol'], float(x['quoteVolume'])] for x in binance.request('get_ticker') if (
      utils.getPrecisionMinusLength(x['lastPrice']) >= 4 and
      x['symbol'] in symbols
    )]
    symbols = sorted(symbols, key=lambda x: x[1], reverse=True)[:length]
    symbols = [x[0] for x in symbols]

    if len(symbols) == 0:
      raise Exception(f'{self.quote} is not a quote asset.')
      exit(1)
    else:
      self.symbols = symbols

  def setLotSize(self):
    balance = binance.getBalance(self.quote)
     
    if self.lotsInUse == 0:
      requiredBalance = self.minNotional * 1.5 * self.riskManagement['lots']
      if binance.getBalance(self.quote) >= requiredBalance or True:
        self.lotSize = balance / self.riskManagement['lots']
        print('[TRADING BOT] Lot size set to {:.8f} {}'.format(self.lotSize, self.quote))
      else:
        print('Waiting for a balance of at least {:.8f} {}...'.format(requiredBalance, self.quote))
        while True:
          if binance.getBalance(self.quote) >= requiredBalance:
            self.lotSize = balance / self.riskManagement['lots']
            print('[TRADING BOT] Lot size set to {:.8f} {}'.format(self.lotSize, self.quote))
            break

          time.sleep(60)

  def socketCallback(self, msg):
    msg = msg['data']['k']
    key = '{}_{}'.format(msg['s'], msg['i'])

    if (msg['t'] == self.lastTrades[msg['s']] or
        msg['s'] in self.mktsCurrTrading or
        self.lotsInUse == self.riskManagement['lots']):
      return

    candleData = [
      float(msg['t']),
      float(msg['o']),
      float(msg['h']),
      float(msg['l']),
      float(msg['c'])
    ]
  
    if msg['t'] == self.candles[key][-1][0]:
      self.candles[key][-1] = candleData
    else:
      self.candles[key].append(candleData)

    for x, y in strategies.strategyDict.items():
      strategy = y(self, key)

      if x in self.strategies: strategy.check()