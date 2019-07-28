from modules import binance

class Strategy:
  def __init__(self, bot, key, name, execute):
    self.bot    = bot
    self.key    = key
    self.name   = name
    self.symbol = key.split('_')[0].upper()

    self.execute = execute

  def openTrade(self, openTime):
    self.bot.mktsCurrTrading.append(self.symbol)
    self.bot.lastTrades[self.symbol] = [self.symbol, openTime]
    self.bot.lotsInUse += 1

    self.socketManager = binance.createSocketManager()
    self.socketManager.start_symbol_ticker_socket(self.symbol, self.execute)
  
  def closeTrade(self):
    self.bot.mktsCurrTrading.pop(self.bot.mktsCurrTrading.index(self.symbol))
    self.bot.lotsInUse -= 1
    self.bot.setLotSize()

    self.socketManager.close()

  def calcOrderSize(self, lotSize, stopSize, maxTradeLoss):
    r = lotSize / (stopSize / maxTradeLoss)

    if r < lotSize:
      return r
    else:
      return lotSize

  def placeOrder(self, side, qty):
    return binance.placeOrder(self.symbol, self.bot.filters[self.symbol], side, qty)
