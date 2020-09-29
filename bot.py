import asyncio
from coinbase.wallet.client import Client
import cbpro
from discord.ext import commands, tasks
from decouple import config

discord_token = config('DISCORD_TOKEN')
coinbase_key = config('COINBASE_KEY')
coinbase_secret = config('COINBASE_SECRET')

client = cbpro.PublicClient()
bot = commands.Bot(command_prefix='!')
priceClient = Client(coinbase_key,coinbase_secret)

cryptoCheck = {}
defaultChannel = -1

@bot.command(name='default', help='Sets the default channel to send messages for big changes of !check currencies'
                                        'to current channel')
async def changeChannel(ctx):
    global defaultChannel
    defaultChannel = ctx.channel.id
    channel = bot.get_channel(defaultChannel)
    await ctx.send('Changed channel for updates to: ' + str(ctx.channel))

@bot.command(name='add', help='!add [crypto] - Inputs valid cryptocurrency for checking for huge changes')
async def addCrypto(ctx, crypt: str, currency='USD'):
    try:
        cPair = '{}-{}'.format(crypt.upper(),currency.upper())
        product = priceClient.get_spot_price(currency_pair=cPair)
        cryptoCheck[crypt.upper()] = product["amount"]
        await ctx.send('```Added: ' + crypt.upper()+'```')
    except:
        await ctx.send("Error: Not a valid input. Check !currencies for a list of available"
                       "valid trading cryptocurrencies")

@bot.command(name='delete', help='!delete [crypto] - Deletes cryptocurrency from checking for huge changes (Opposite effect of !add)')
async def delCrypto(ctx, crypt: str):
    try:
        cryptoCheck.pop(crypt.upper())
        await ctx.send('```Deleted: ' +crypt.upper()+'```')
    except:
        await ctx.send("Error: Not a valid input. Check !currencies for a list of available"
                       "valid trading cryptocurrencies")

@bot.command(name='check', help="Manually checks current prices of !add'ed cryptocurrencies")
async def checkCrypto(ctx):
    try:
        concatenatedString = '```'
        if len(cryptoCheck) == 0:
            raise Exception('Error: Empty list, try adding some cryptocurrencies using !add')
        for k,v in cryptoCheck.items():
            concatenatedString += f'{k}: ${v}\n'
        await ctx.send(concatenatedString+ '```')
    except:
        await ctx.send("Error: Empty list, try adding some cryptocurrencies using !add")

@tasks.loop(seconds=15)
async def updateDict():
    for k in cryptoCheck.keys():
        cPair = k+'-USD'
        price = priceClient.get_spot_price(currency_pair=cPair)
        cryptoCheck[k] = price['amount']

@tasks.loop(minutes=5)
async def checkChanges():
    global defaultChannel
    cryptoPercentage = {}
    concatenatedString = '```BIG CHANGES HAVE OCCURRED:\n'
    for k in cryptoCheck.keys():
        cPair = k+'-USD'
        product = client.get_product_24hr_stats(cPair)
        price = cryptoCheck[k]
        open24 = product['open']
        percentage = round((((float(price) - float(open24))/float(open24))*100),3)
        if (percentage >= 2.5) or (percentage <= -2.5):
            cryptoPercentage[k] = percentage
    if len(cryptoPercentage) > 0:
        for k,v in cryptoPercentage.items():
            concatenatedString += f'{k}: 24 Hour Percentage {v}%\n'
        channel = bot.get_channel(defaultChannel)
        await channel.send(concatenatedString[0:-1]+'```')
        await asyncio.sleep(3600)

@bot.command(name='time', help='Displays current server time(Coinbase)')
async def server_time(ctx):
    sTime = client.get_time()
    date = sTime["iso"][0:10]
    time = sTime['iso'][11:-1]
    response = "```Server Date: {} \nServer Time: {} UTC```".format(date,time)
    await ctx.send(response)

@bot.command(name='currencies', help='Displays all available trading currencies')
async def currencies(ctx):
    concatenatedString = ''
    productDictionary = {}
    products = client.get_currencies()
    for i in products:
        if i['details']['type'] == 'crypto':
            productDictionary[i['id']] = i['name']
    sortedDict = dict(sorted(productDictionary.items(), key=lambda item: item[0]))
    for k,v in sortedDict.items():
        concatenatedString += f'{k}: {v}\n'
    await ctx.send('```' + concatenatedString[0:-2] + ' ```')

@bot.command(name='24stats', help="!24stats [crypto] - Displays 24 hours stats of a specific currency"
                                  "(24 Hour Open, 24 Hour High, 24 Hour Low, 24 Hour Change (%))")
async def stats24Hours(ctx, crypt: str, currency='USD'):
    try:
        cPair = '{}-{}'.format(crypt.upper(),currency.upper())
        product = client.get_product_24hr_stats(cPair)
        price = priceClient.get_spot_price(currency_pair=cPair)['amount']
        open24 = product['open']
        high24 = product['high']
        low24 = product['low']
        percentage = round((((float(price) - float(open24))/float(open24))*100),3)
        await ctx.send(f'```Open: {open24}\nHigh: {high24}\nLow: {low24}\nPercentile Change: {percentage}%```')
    except:
        await ctx.send("Error: Not a valid input. Check !currencies for a list of available"
                       "valid trading cryptocurrencies")


@stats24Hours.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Error: Missing input. "
                       "Put in cryptocurrency symbol w/ optional currency "
                       "(ex:!price \"btc\" USD or !price \"eth\" GBP)")

@bot.command(name='price', help="!price [crypto] - Displays price of specified currency")
async def price_display(ctx, crypt: str, currency='USD'):
    try:
        cPair = '{}-{}'.format(crypt.upper(),currency.upper())
        product = priceClient.get_spot_price(currency_pair=cPair)
        price = product['amount']
        time = client.get_time()['iso'][11:-1]
        listing = "```The price of {} at {} UTC: ${}```".format(crypt.upper(),time,price)
        await ctx.send(listing)
    except:
        await ctx.send("Error: Not a valid input. Check !currencies for a list of available"
                       "valid trading cryptocurrencies")

@price_display.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Error: Missing input. "
                       "Put in cryptocurrency symbol w/ optional currency "
                       "(ex:!price \"btc\" USD or !price \"eth\" GBP)")

updateDict.start()
checkChanges.start()
print("Bot has successfully been deployed.")
bot.run(discord_token)
