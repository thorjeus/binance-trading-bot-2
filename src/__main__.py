import time
import threading

from modules import binance
from modules import utils
from bot.trading_bot import TradingBot
from bot.arbitrage_bot import ArbitrageBot
from bot import strategies

def mainMenu():
  utils.clearTerminal()
  
  print('Welcome!\nWhat would you like to do?\n')
  print('[1] Start trading and arbitrage')
  print('[2] Start trading')
  print('[3] Start arbitrage')
  print('[4] Set Binance API keys')
  print('[5] Set bot parameters')
  print('[0] Exit')

  while True:
    choice = input('\nChoice: ')

    if choice == '1':
      utils.clearTerminal()
      try:
        utils.loadJSON('config/binance.json')
        config = utils.loadJSON('config/bot.json')
        workers = [
          threading.Thread(target=TradingBot(config).startTrading),
          threading.Thread(target=ArbitrageBot(config).startArbitrage)
        ]
        for worker in workers:
          worker.start()

        break
      except:
        print("Looks like you didn't set the configurations yet.")
        time.sleep(2)
        mainMenu()
    elif choice == '2':
      utils.clearTerminal()
      try:
        utils.loadJSON('config/binance.json')
        config = utils.loadJSON('config/bot.json')
        TradingBot(config).startTrading()
      except Exception as e:
        print(e)
        print("Looks like you didn't set the configurations yet.")
        time.sleep(2)
        mainMenu()
    elif choice == '3':
      utils.clearTerminal()
      try:
        utils.loadJSON('config/binance.json')
        config = utils.loadJSON('config/bot.json')
        ArbitrageBot(config).startArbitrage()
      except:
        print("Looks like you didn't set the configurations yet.")
        time.sleep(2)
        mainMenu()
    elif choice == '4':
      setBinanceAPIKeys()
    elif choice == '5':
      setBotParameters()
    elif choice == '0':
      exit(0)
    else:
      print('Invalid choice.')

def setBinanceAPIKeys():
  utils.clearTerminal()

  print('Binance API configuration\n')
  
  key    = input('API key: ')
  secret = input('API secret: ')

  utils.clearTerminal()
  
  binanceConfig = {
    'key': key,
    'secret': secret
  }

  utils.dumpJSON(binanceConfig, 'config/binance.json')

  print('\nConfiguration saved!')
  time.sleep(2)

  mainMenu()

def setBotParameters():
  utils.clearTerminal()

  botConfig = {
    'stablecoins': [ 
      'USDT',
      'PAX',
      'TUSD',
      'USDC',
      'USDS',
      'USDSB'
    ],
    'riskManagement': {},
    'fee': .1
  }

  print('Trading configuration\n')

  botConfig['quote']      = input('Quote asset: ')
  botConfig['marketNum']  = int(input('Number of markets: '))
  botConfig['timeframes'] = input('Timeframes (i.e.: 15m, 30m, 1h): ').split(',')
  botConfig['timeframes'] = [x.strip() for x in botConfig['timeframes']]

  strategyNames = list(strategies.strategyDict.keys())
  choices       = []
  while True:
    utils.clearTerminal()
    
    print('Strategies:\n')
    for x, y in enumerate(strategyNames):
      print(f'[{x + 1}] {y}')
    print('[0] Done')

    choice = int(input('Choice: '))
    if choice == 0:
      if len(choices) == 0:
        continue
      else:
        break
    else:
      choices.append(strategyNames[choice - 1])
      strategyNames.pop(choice - 1)
  botConfig['strategies'] = choices

  utils.clearTerminal()

  print('\nRisk management\n')

  botConfig['riskManagement']['lots']            = int(input('Number of lots to split balance in (Each lot is used for each trade): '))
  botConfig['riskManagement']['maxLossPerTrade'] = float(input('Max loss per trade (percentage): '))
  
  utils.dumpJSON(botConfig, 'config/bot.json')
  print('\nConfiguration saved!')
  time.sleep(2)

  mainMenu()

mainMenu()
