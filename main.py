import discord
from discord.ext import commands

import os, sys, traceback

"""Based on https://gist.github.com/EvieePy/d78c061a4798ae81be9825468fe146be"""

def get_prefix(bot, message):
    prefixes = ['!', '.']

    return commands.when_mentioned_or(*prefixes)(bot, message)

initial_extensions = ['plugins.chaintracker',
                      'plugins.faction',
                      'plugins.misc',
                      'plugins.owner',
                      'plugins.weather']

bot = commands.Bot(command_prefix=get_prefix, description='TWR Discord bot (maintained by cottongin)')

if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print(f'Failed to load extension {extension}.', file=sys.stderr)
            traceback.print_exc()


@bot.event
async def on_ready():

    print(f'\n\nLogged in as: {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    activity = discord.Game(name='TORN CITY')
    await bot.change_presence(activity=activity)
    print(f'Successfully logged in and booted...!')

#keep_alive()
token = os.getenv("BOT_SECRET")
#print(token)
bot.run(token, bot=True, reconnect=True)