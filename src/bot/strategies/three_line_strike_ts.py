from modules import Strategy
from modules import binance
from modules import utils

class ThreeLineStrikeTs(Strategy):
  def __init__(self, bot, key):
    super().__init__(
      bot=bot,
      key=key,
      name='Three Line Strike (with trailing stop)',
      execute=self.execute
    )

  def check(self):
    candles = self.bot.candles[self.key]
    
    if list(map(lambda x: x[4] < x[1], candles[-4:-1])).count(False) > 0:
      return
    
    close          = candles[-1][4]
    prevCandleSize = utils.getPercentChange(candles[-2][3], candles[-2][2])
    currCandleSize = utils.getPercentChange(candles[-1][3], candles[-1][2])
    self.trigger   = utils.changeByPercent(candles[-2][2], .05)
    
    if close > self.trigger or True:
      if candles[-2][3] > candles[-1][3]:
        self.stop = utils.changeByPercent(candles[-1][3], -self.bot.fee)
      else:  
        self.stop = utils.changeByPercent(candles[-2][3], -self.bot.fee)

      self.stopSizePerc = utils.getPercentChange(self.stop, close)
      self.tsTrigger    = utils.changeByPercent(close, self.stopSizePerc / 2)
      if self.stopSizePerc < .4 or self.stopSizePerc > 3: return

      quoteQty = self.calcOrderSize(self.bot.lotSize, self.stopSizePerc, self.bot.riskManagement['maxLossPerTrade'])

      if quoteQty > self.bot.minNotional:
        buy = self.placeOrder('buy', quoteQty / candles[-1][1])
      else:
        return

      self.sellQuantity = utils.changeByPercent(float(buy['executedQty']), -self.bot.fee)
      self.higherPrice  = close

      print(f'\n[TRADING BOT] {self.key.upper()} trade started')
      print(f'[TRADING BOT] {self.key.upper()} Bought @ {close} {self.bot.quote}')

      self.openTrade(candles[-1][0])

  def execute(self, msg):
    bid = float(msg['b'])

    if self.stop >= bid:
      self.placeOrder('sell', self.sellQuantity)

      print(f'[TRADING BOT] {self.key.upper()} sold @ {bid} {self.bot.quote}')
      if bid > self.trigger:
        print(f'[TRADING BOT] {self.key.upper()} trade closed (profit)\n')
      else:
        print(f'[TRADING BOT] {self.key.upper()} trade closed (loss)\n')
      self.closeTrade()
    elif bid > self.tsTrigger and bid > self.higherPrice:
      self.stop = utils.changeByPercent(bid, -(self.stopSizePerc / 2))
    if bid > self.higherPrice: self.higherPrice = bid