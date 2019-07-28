import os
import json
import math
import platform

system = platform.system()

def loadJSON(path):
  with open(os.path.join(os.getcwd(), ('../' if system == 'Windows' else '') + path), 'r') as f:
    return json.loads(f.read())

def dumpJSON(data, path):
  path = os.path.join(os.getcwd(), path)
  try:
    os.makedirs('/'.join(path.split('/')[:-1]))
  except:
    pass
  with open(path, 'w') as f:
    json.dump(data, f, indent=2)

def getPrecisionMinusLength(floatStr):
  floatStr = floatStr.replace('.', '')

  count = 0
  for c in floatStr:
    if c != '0': break

    count += 1

  return len(floatStr) - count

def truncate(f, n):
  return math.floor(f * 10 ** n) / 10 ** n

def formatFloat(quantity, filtr):
  return truncate(quantity, str(filtr).replace('.', '').find('1'))

def changeByPercent(number, percent):
  if number > 0:
    return number + number * percent / 100
  else:
    return number - number * percent / 100

def getPercentChange(initial, final):
  return (final - initial) / initial * 100

def clearTerminal():
  if system == 'Linux' or system == 'Darwin':
    os.system('clear')
  elif system == 'Windows':
    os.system('cls')
  