import time

from modules import binance
from modules import utils

class ArbitrageBot():
  def __init__(self, config):
    self.fee         = config['fee']
    self.quote       = config['quote']
    self.stablecoins = config['stablecoins']
    self.symbols     = {}
    self.markets     = {}
    self.prevQty     = 0

  def startArbitrage(self):
    self.setTradingSymbols()

    print(f'[ARBITRAGE BOT] Loading {self.quote} balance...')
    self.balance = binance.getBalance(self.quote)

    print('[ARBITRAGE BOT] Connected to websockets, arbitrage started.')
    socketManager = binance.createSocketManager()
    socketManager.start_user_socket(self.handleBalanceSocketMsg)
    socketManager.start_multiplex_socket([f'{x.lower()}@depth5' for x in self.symbols.keys()], self.handleBookSocketMsg)
    socketManager.run()

  def setTradingSymbols(self):
    print('[ARBITRAGE BOT] Loading symbols info...')
    for info in binance.request('get_exchange_info')['symbols']:
      if info['status'] != 'TRADING': continue

      for filtr in info['filters']:
        if filtr['filterType'] == 'LOT_SIZE':
          lotSize = filtr['stepSize']

      self.symbols[info['symbol']] = {
        'lotSize': lotSize,
        'base': info['baseAsset'],
        'quote': info['quoteAsset']
      }

    if len(self.symbols) == 0:
      raise Exception(f'{self.quote} is not a quote asset.')
      exit(1)

  def handleBalanceSocketMsg(self, msg):
    if msg['e'] == 'outboundAccountInfo':
      self.balance = [float(x['f']) for x in msg['B'] if x['a'] == self.quote][0]

  def handleBookSocketMsg(self, msg):
    symbol = msg['stream'].split('@')[0].upper()

    bids = [[float(y) for y in x] for x in msg['data']['bids']]
    asks = [[float(y) for y in x] for x in msg['data']['asks']]

    step1_market = {
      'lotSize': self.symbols[symbol]['lotSize'],
      'base': self.symbols[symbol]['base'],
      'quote': self.symbols[symbol]['quote'],
      'bids': bids,
      'asks': asks
    }
    self.markets[symbol] = step1_market

    base  = step1_market['base']
    quote = step1_market['quote']

    if quote == self.quote:
      if quote in self.stablecoins:
        # When the asset bought hasn't a market where it is the quote asset
        conditions = [
          lambda symbol, base: symbol['base'] == base and symbol['quote'] not in self.stablecoins,
          lambda symbol, step2_market: symbol['base'] == step2_market['quote'] and symbol['quote'] == self.quote
        ]
        stepSides        = ['sell', 'sell']
        buyPriceCalcule  = lambda step1, step2, step3: step1 / step2
        sellPriceCalcule = lambda step1, step2, step3: step3
        
        if self.verifyArbitrage(step1_market, conditions, stepSides, buyPriceCalcule, sellPriceCalcule):
          return

        # When the asset bought has a market where it is the quote asset
        conditions = [
          lambda symbol, base: symbol['quote'] == base and symbol['quote'] not in self.stablecoins,
          lambda symbol, step2_market: symbol['base'] == step2_market['base'] and symbol['quote'] == self.quote
        ]
        stepSides        = ['buy', 'sell']
        buyPriceCalcule  = lambda step1, step2, step3: step1
        sellPriceCalcule = lambda step1, step2, step3: step3 / step2

        if self.verifyArbitrage(step1_market, conditions, stepSides, buyPriceCalcule, sellPriceCalcule):
          return

  def calculateOrder(self, side, book, balance):
    if side == 'buy':
      baseVolume = 0
      for order in book:
        if balance - order[0] * order[1] < 0:
          baseVolume += balance / order[0]
          balance     = 0
          break
        else:
          baseVolume += balance / order[0]
          balance    -= order[0] * order[1]

      if balance == 0:
        return [order[0], baseVolume]
    elif side == 'sell':
      baseVolume  = balance
      quoteVolume = 0
      for order in book:
        if baseVolume - order[1] < 0:
          quoteVolume += baseVolume * order[0]
          baseVolume   = 0
          break
        else:
          quoteVolume += baseVolume * order[0]
          baseVolume  -= order[1]

      if baseVolume == 0:
        return [order[0], quoteVolume]

  def verifyArbitrage(self, step1_market, conditions, stepSides, buyPriceCalcule, sellPriceCalcule):
    step2_markets = [x for x in self.markets.values() if conditions[0](x, step1_market['base'])]
    if len(step2_markets) > 0:
      for step2_market in step2_markets:
        step3_markets = [x for x in self.markets.values() if conditions[1](x, step2_market)]
        if len(step3_markets) > 0:
          step3_market = step3_markets[0]

          step1_priceAndQty = self.calculateOrder(
            'buy',
            step1_market['asks'],
            self.balance
          )
          if not step1_priceAndQty: continue
          step2_priceAndQty = self.calculateOrder(
            stepSides[0],
            step2_market['bids' if stepSides[0] == 'sell' else 'asks'],
            step1_priceAndQty[1]
          )
          if not step2_priceAndQty: continue
          step3_priceAndQty = self.calculateOrder(
            stepSides[1],
            step3_market['bids' if stepSides[1] == 'sell' else 'asks'],
            step2_priceAndQty[1]
          )
          if not step3_priceAndQty: continue

          if not (step1_priceAndQty and step2_priceAndQty and step3_priceAndQty):
            continue

          buyPrice  = buyPriceCalcule(step1_priceAndQty[0], step2_priceAndQty[0], step3_priceAndQty[0])
          sellPrice = sellPriceCalcule(step1_priceAndQty[0], step2_priceAndQty[0], step3_priceAndQty[0])
          spread    = utils.getPercentChange(buyPrice, sellPrice) - self.fee * 3 # Spread minus order fees

          if spread >= 1:
            order1 = binance.placeOrder(
              step1_market['base'] + step1_market['quote'],
              step1_market['lotSize'],
              'buy',
              step1_priceAndQty[1]
            )
            execQty   = utils.changeByPercent(float(order1['executedQty']), -self.fee)
            execPrice = float(order1['fills'][0]['price'])

            order2 = binance.placeOrder(
              step2_market['base'] + step2_market['quote'],
              step2_market['lotSize'],
              stepSides[0],
              execQty if stepSides[0] == 'sell' else execQty / step2_priceAndQty[0]
            )

            execQty   = utils.changeByPercent(float(order2['executedQty']), -self.fee)
            execPrice = float(order2['fills'][0]['price'])
            
            if stepSides[0] == 'sell' and stepSides[1] == 'sell':
              execQty = execQty * execPrice
            elif stepSides[1] == 'sell':
              pass
            else:
              execQty = execQty / step3_priceAndQty[0]

            order3 = binance.placeOrder(
              step3_market['base'] + step3_market['quote'],
              step3_market['lotSize'],
              stepSides[1],
              execQty
            )
            print('[Arbitrage done] Market: {} Spread: {:.2f}%'.format(step1_market['base'] + step1_market['quote'], spread))

            self.balance = binance.getBalance(self.quote)
            return True
          else:
            continue