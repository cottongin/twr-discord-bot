import asyncio
import pendulum
#import discord
import aiohttp
from discord.ext import commands
import os

class ChainTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.key = os.getenv("TORN_KEY")
        self.current_chain = 0
        #self.heartbeat_task = self.bot.loop.create_task(self.heartbeat())

    async def heartbeat(self, ctx):
        print("ChainTracker: Initialized")
        print("ChainTracker: checking for chain")
        url = "https://api.torn.com/faction/?selections=chain&key={}".format(self.key)
        #channel = ctx.get_channel(550084148426047509) # channel ID goes here
        first = False
        announced = []
        chains_to_announce = [
            24,25,49,50,99,100,249,250,499,500,
            999, 1000, 2499, 2500, 4999, 5000,
            9999, 10000, 24999, 25000,
            49999, 50000, 99999, 100000
        ]
        while True:
            #print("ChainTracker: checking for chain")
            session = aiohttp.ClientSession()
            async with session.get(url) as resp:
                #print(await resp.json())
                data = await resp.json()
                #print(len(data))
            await session.close()
            if not data: return
            chain = data['chain']
            #print(chain)
            if first:
                now = pendulum.now()
                expires = pendulum.from_timestamp(chain['timeout'])
                if chain['current'] in chains_to_announce and chain['current'] not in announced:
                    await ctx.send('**{} HIT CHAIN** achieved'.format(chain['current']))
                    announced.append(chain['current'])    
                difference = now.diff(expires).in_seconds()
                print(difference)
                if difference <= 30:
                    await ctx.send('@everyone **{} hit chain** expires in **{} seconds**!'.format(
                        chain['current'],
                        difference
                    ))
            if chain['current'] >= 10 and not first:
                await ctx.send('@everyone **NEW CHAIN detected!**')
                first = True

            if chain['current'] == 0 and first:
                await ctx.send('Chain expired')
                print('Chain expired')
                first = False
            if chain['current'] > 0:
                print('Current chain: {}'.format(chain['current']), end="\r", flush=True)
            await asyncio.sleep(10) # task runs every 60 seconds

    # async def on_ready(self):
    #     self.heartbeat_task = self.bot.loop.create_task(self.heartbeat())

    @commands.command(pass_context=True, hidden=True)
    @commands.has_permissions(administrator=True)
    async def stop(self, ctx):
        self.heartbeat_task.cancel()
        await ctx.send('ChainTracker stopped by {}'.format(ctx.message.author.name))

    @commands.command(pass_context=True, hidden=True)
    @commands.has_permissions(administrator=True)
    async def start(self, ctx):
        self.heartbeat_task = self.bot.loop.create_task(self.heartbeat(ctx))
        await ctx.send('ChainTracker started by {}'.format(ctx.message.author.name))

def setup(bot):
    bot.add_cog(ChainTracker(bot))