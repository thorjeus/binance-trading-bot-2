from modules import Strategy
from modules import binance
from modules import utils

class ThreeLineStrike(Strategy):
  def __init__(self, bot, key):
    super().__init__(
      bot=bot,
      key=key,
      name='Three Line Strike',
      execute=self.execute
    )

  def check(self):
    candles = self.bot.candles[self.key]
    
    if list(map(lambda x: x[4] < x[1], candles[-4:-1])).count(False) > 0:
      return
    
    prevCandleSize = utils.getPercentChange(candles[-2][3], candles[-2][2])
    currCandleSize = utils.getPercentChange(candles[-1][3], candles[-1][2])
    trigger        = utils.changeByPercent(candles[-2][2], .05)
    entry          = candles[-1][4]

    if entry > trigger:
      if candles[-2][3] > candles[-1][3]:
        self.sl = utils.changeByPercent(candles[-1][3], -self.bot.fee)
      else:  
        self.sl = utils.changeByPercent(candles[-2][3], -self.bot.fee)

      stopSizePerc = utils.getPercentChange(self.sl, entry)
      if stopSizePerc < .4 or stopSizePerc > 2: return
      
      self.tp = utils.changeByPercent(candles[-2][2], prevCandleSize)

      quoteQty = self.calcOrderSize(self.bot.lotSize, stopSizePerc, self.bot.riskManagement['maxLossPerTrade'])

      if quoteQty > self.bot.minNotional:
        buy = self.placeOrder('buy', quoteQty / candles[-1][1])
      else:
        return

      self.sellQuantity = utils.changeByPercent(float(buy['executedQty']), -self.bot.fee)

      print(f'\n[TRADING BOT] {self.key.upper()} trade started')
      print(f'[TRADING BOT] {self.key.upper()} bought @ {entry} {self.bot.quote}')

      self.openTrade(candles[-1][0])

  def execute(self, msg):
    bid = float(msg['b'])
    
    if self.tp <= bid:
      self.placeOrder('sell', self.sellQuantity)

      print(f'[TRADING BOT] {self.key.upper()} sold @ {bid} {self.bot.quote}')
      print(f'[TRADING BOT] {self.key.upper()} trade closed (profit)\n')

    elif self.sl >= bid:
      self.placeOrder('sell', self.sellQuantity)

      print(f'[TRADING BOT] {self.key.upper()} sold @ {bid} {self.bot.quote}')
      print(f'[TRADING BOT] {self.key.upper()} trade closed (loss)\n')
    else:
      return

    self.closeTrade()