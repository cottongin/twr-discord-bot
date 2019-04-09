from discord.ext import commands
import random

class Misc(commands.Cog):
    """Fun and other commands that don't belong anywhere else"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['version'])
    @commands.guild_only()
    async def source(self, ctx):
        """Replies with link to my source code"""
        await ctx.send("See my source code here: https://repl.it/@cottongintonic/TWRBot")

    @commands.command()
    async def flip(self, ctx, *, times: int=1):
        """Flips a coin X(1) times"""
        if times > 100: times = 100
        if times <= 0: times = 1

        flips = [random.randint(0,1) for r in range(times)]
        results = []
        for flip in flips:
            if flip == 0: results.append('Heads')
            elif flip == 1: results.append('Tails')

        if times == 1:
            reply = f"I flipped **{results[0]}**"
        else:
            reply = f"I flipped **Heads {results.count('Heads')} times** and **Tails {results.count('Tails')} times**"
        await ctx.send(reply)

    @commands.command()
    async def pants(self, ctx):
        """PANTS!"""
        await ctx.send("https://www.youtube.com/watch?v=eB5EE42So7I")

def setup(bot):
    bot.add_cog(Misc(bot))