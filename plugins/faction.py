# import asyncio
import discord
# import aiohttp
from discord.ext import commands
import os, pickle
import requests, pendulum, redis
import jicson, json
from plugins.helpers import _helperFuncs

class Faction(commands.Cog):
    """Faction information and related commands"""
    def __init__(self, bot):
        self.bot = bot
        self.key = os.getenv("TORN_KEY")
        self.db = redis.from_url(os.environ.get("REDIS_URL"))
        try:
            tmp = self.db.get('factions')
            self.factions = pickle.loads(tmp)
        except:
            self.factions = {}
    #     try:
    #         self.nextchain = self._load_chain_cache()
    #     except:
    #         self.nextchain = []

    # def _load_chain_cache(self):
    #     with open('scheduled_chains.db', 'rb') as handle:
    #         b = pickle.load(handle)
    #     return b

    # def _dump_chain_cache(self):
    #     with open('scheduled_chains.db', 'wb') as handle:
    #         pickle.dump(self.nextchain, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # @commands.command()
    # @commands.guild_only()
    # async def register(self, ctx):
    #     """Register with the bot"""

    # @commands.command()
    # @commands.guild_only()
    # async def travel(self, ctx, *, member: str):
    #     """Checks travel for given member"""
    #     member = member.lower()
    #     url = "https://api.torn.com/faction/?selections=basic&key={}".format(self.key)
    #     try:
    #         data = requests.get(url).json()
    #     except:
    #         await ctx.send("Error fetching data")
    #         return
    #     members = data['members']
    #     memberId = None
    #     for mid, m in members.items():
    #         if m['name'].lower() == member:
    #             memberId = mid
    #             name = m['name']
    #             break
    #     if not memberId:
    #         await ctx.send("I couldn't find anyone in the faction by that name")
    #         return
        
    #     travel_url = "https://api.torn.com/user/{}?selections=travel&key={}".format(memberId, self.key)
    #     try:
    #         data = requests.get(travel_url).json()
    #     except:
    #         await ctx.send("Error fetching data")
    #         return

    #     travel = data['travel']

    #     reply = "{} is headed to {}.  They'll land there in about {} minutes.".format(
    #         name,
    #         travel['destination'],
    #         round(int(travel['time_left']//60))
    #     )

    #     await ctx.send(reply)

    @commands.command(name='link')
    @commands.has_permissions(administrator=True)
    async def linkguild(self, ctx, *, text: str):
        """Links a Discord <guild> to a Torn API <key>"""
        if len(text.split()) > 2:
            await ctx.send("Invalid format! (guild/faction key)")
            return
        guild = text.split()[0]
        key = text.split()[1]
        self.factions[guild] = key
        tmp = pickle.dumps(self.factions, protocol=pickle.HIGHEST_PROTOCOL)
        self.db.set("factions", tmp)
        await ctx.send("Done!")


    @commands.command(aliases=['g'])
    async def guild(self, ctx):
        """Returns guild"""
        await ctx.send(ctx.guild.id)

    @commands.command(aliases=['info'])
    async def factioninfo(self, ctx, *, faction: str=""):
        """Returns basic information on the faction"""
        guild_id = faction.upper() or str(ctx.guild.id)
        if guild_id not in self.factions:
            await ctx.send("No Torn API key has been assigned for this Discord server or provided faction")
            return
        print(self.factions[guild_id])
        url = "https://api.torn.com/faction/?selections=basic,stats&key={}".format(self.factions[guild_id])
        try:
            data = requests.get(url).json()
        except:
            await ctx.send("Error fetching data")
            return

        #print(data)

        name = "{}".format(_helperFuncs.bold(data['name']))
        members = "**Members:** {}".format(len(data['members']))
        oldest = None
        days = 0
        for _,member in data['members'].items():
            #print(member)
            if member['days_in_faction'] > days:
                oldest = member
                days = member['days_in_faction']
        oldest_p = "**Veteran Member:** {} ({} days in faction)".format(oldest['name'], oldest['days_in_faction'])

        members += " | {}".format(oldest_p)
        best_chain = "**Best Chain:** {} (!bc for more info)".format(data['best_chain'])

        try:
            leaders = "**Leader:** {} | **Co-Leader:** {}".format(
                data['members'][str(data['leader'])]['name'],
                data['members'][str(data['co-leader'])]['name']
            )
        except:
            leaders = ""
            pass
        
        respect = "**Respect:** {}".format(data['respect'])
        respect += " | {}".format(best_chain)

        lines = [name, leaders, respect, members]

        reply = "\n".join(lines)

        await ctx.send(reply)

    @commands.command(aliases=['c'])
    async def chain(self, ctx):
        """Checks for a current chain"""
        url = "https://api.torn.com/faction/?selections=chain&key={}".format(self.key)
        try:
            data = requests.get(url).json()
        except:
            await ctx.send("Error fetching data :(")
            return

        cooldown = None
        chain = data.get('chain')
        if not chain:
            await ctx.send("No chain detected.")
            return
        if chain['current'] == 0:
            if chain['cooldown'] != 0:
                cooldown = chain['cooldown']
            reply = "No active chain detected."
            if cooldown:
                reply += "\nCooldown from previous chain: {}".format(cooldown)
        else:
            now = pendulum.now()
            expires = pendulum.now("UTC").add(seconds=chain['timeout'])
            #print(expires)
            expiry = now.diff(expires, True).in_words()
            expiry = "It expires in **{}**".format(expiry)
            if chain['cooldown'] != 0:
                cooldown = pendulum.now("UTC").add(seconds=chain['cooldown'])
                #cooldown = chain['cooldown']
                expiry = "Cooldown active: **{}**".format(now.diff(cooldown, True).in_words())
            reply = "There is a **{}** hit chain active!\n{}.".format(
                chain['current'],
                expiry,
            )

        await ctx.send(reply)

    # @commands.command(aliases=['nc'], usage="add 'True' to mention everyone")
    # @commands.guild_only()
    # async def nextchain(self, ctx, *, notify: bool=False):
    #     """Replies with the next scheduled chain"""
    #     if not self.nextchain:
    #         await ctx.send("No chain planned.")
    #         return
    #     self.nextchain = sorted(self.nextchain)
    #     now = pendulum.now('UTC')
    #     if self.nextchain[0] < now:
    #         self.nextchain = self.nextchain[1:]
    #         self._dump_chain_cache()

    #     if notify:
    #         prepend = "@everyone "
    #     else:
    #         prepend = ""
        
    #     now = pendulum.now('UTC')
    #     diff = self.nextchain[0].diff(now).in_words()
    #     if "seconds" in diff:
    #         diff = diff.split()
    #         diff = " ".join(diff[:-2])

    #     reply = "{}Our next scheduled chain is: **{} TCT**\n(in {})".format(prepend, self.nextchain[0].format("dddd, MMM Do HH:mm"), diff)

    #     await ctx.send(reply)

    # @commands.command(aliases=['lc'])
    # @commands.guild_only()
    # async def listchains(self, ctx):
    #     """Lists all scheduled chains"""
    #     output_format = "dddd, MMM Do HH:mm"
    #     if not self.nextchain:
    #         await ctx.send("No chains planned.")
    #         return
    #     self.nextchain = sorted(self.nextchain)
    #     now = pendulum.now('UTC')
    #     if self.nextchain[0] < now:
    #         self.nextchain = self.nextchain[1:]
    #         self._dump_chain_cache()

    #     await ctx.send("The following chains are planned:\n{}".format(
    #         "\n".join(["{}. {} TCT".format(n+1, c.format(output_format)) for n,c in enumerate(self.nextchain)])
    #     ))

    # @commands.command(aliases=['rc'])
    # @commands.has_permissions(administrator=True)
    # async def removechain(self, ctx, *, chain: int):
    #     """Removes a scheduled chain"""
    #     output_format = "dddd, MMM Do HH:mm"
    #     if not self.nextchain:
    #         await ctx.send("No chains planned.")
    #         return
    #     # self.nextchain = sorted(self.nextchain)
    #     # now = pendulum.now('UTC')
    #     # if self.nextchain[0] < now:
    #     #     self.nextchain = self.nextchain[1:]
    #     #     self._dump_chain_cache()
    #     removed_chain = self.nextchain.pop(chain-1)
    #     self.nextchain = sorted(self.nextchain)
    #     self._dump_chain_cache()
    #     await ctx.send("I removed '{} TCT' from the schedule".format(removed_chain.format(output_format)))
        

    # @commands.command(aliases=['sc'], usage="date & time in TCT (ex: Mar 1st 2019 16:00)")
    # @commands.has_permissions(administrator=True)
    # async def schedulechain(self, ctx, *, dateTime: str):
    #     """Schedule a chain"""
    #     output_format = "dddd, MMM Do HH:mm"
    #     if self.nextchain:
    #         self.nextchain = sorted(self.nextchain)
    #         now = pendulum.now('UTC')
    #         if self.nextchain[0] < now:
    #             self.nextchain = self.nextchain[1:]
    #             self._dump_chain_cache()
    #     # if self.nextchain:
    #     #     await ctx.send("(FYI there's already a scheduled chain!\n{}".format(self.nextchain[0].format(output_format)))

    #     try:
    #         tmp = pendulum.parse(dateTime, tz='UTC', strict=False)
    #         self.nextchain.append(tmp)
    #         self.nextchain = sorted(self.nextchain)
    #     except:
    #         await ctx.send("I couldn't parse your input")
    #         return

    #     self._dump_chain_cache()
    #     await ctx.send("Chain scheduled for {} TCT!".format(tmp.format(output_format)))
    #     #now = pendulum.now("UTC")
    #     diff = self.nextchain[0].diff_for_humans()

    #     reply = "Our **next** scheduled chain is: **{} TCT**\n({})".format(self.nextchain[0].format(output_format), diff)

    #     await ctx.send(reply)

    @commands.command(aliases=['bc'])
    async def bestchain(self, ctx):
        """Gets our best chain"""
        url = "https://api.torn.com/faction/?selections=basic,chains,attacksfull&key={}".format(self.key)
        print(url)
        try:
            data = requests.get(url).json()
        except:
            await ctx.send("Error fetching data :(")
            return

        best = 0
        bc = None
        #bcid = None
        for _,item in data['chains'].items():
            if item['chain'] > best:
                best = item['chain']
                bc = item
                #bcid = id_

        chain = bc['chain']
        respect = bc['respect']
        start = bc['start']
        stop = bc['end']
        leaders = {}
        for _,item in data['attacks'].items():
            if start <= item['timestamp_started'] < stop:
                if item['attacker_id'] in leaders:
                    leaders[item['attacker_id']]['respect'] += float(item['respect_gain'])
                    leaders[item['attacker_id']]['count'] += 1
                else:
                    leaders[item['attacker_id']] = {}
                    leaders[item['attacker_id']]['respect'] = float(item['respect_gain'])
                    leaders[item['attacker_id']]['count'] = 1
        sorted_by_value = sorted(leaders.items(), key=lambda kv: kv[1]['respect'], reverse=True)
        #print(sorted_by_value)
        leaders = {}
        for item in sorted_by_value[:5]:
            #print(data['members'][str(item[0])]['name'])
            leaders[data['members'][str(item[0])]['name']] = item[1]
        padding = 0
        for item in leaders:
            if len(item) > padding:
                padding = len(item)
        #print(leaders)
        strings = []
        for k,v in leaders.items():
            strings.append("{:{width}}(x{})\t{:+7.2f} respect".format(k,v['count'],v['respect'],width=padding))
        if strings:
            leader_string = "\n**Top 5 Attackers:**\n```{}```".format(
                "\n".join(strings)
            )
        start = pendulum.from_timestamp(start)
        start_p = start.format('MMM Do, YYYY, HH:mm')
        stop = pendulum.from_timestamp(stop)
        stop_p = stop.format('MMM Do, YYYY, HH:mm')

        duration = stop.diff(start, True).in_words()

        reply = f"Our best chain happened from **{start_p}** to **{stop_p}**.\nWe gained **{respect}** respect.\nIt lasted **{chain}** attacks. [**{duration}**]{leader_string if strings else ''}"
        #print(reply)
        await ctx.send(reply)

    @commands.command(aliases=['cal', 'nc', 'lc'], usage="add 'notify' to mention everyone")
    @commands.guild_only()
    async def calendar(self, ctx, *args):
        """Fetches next event from TWR Faction calendar"""
        print(args)
        number = 5
        notify = ''
        for arg in args:
            if arg.isdigit():
                number = int(arg)
            else:
                notify = arg
        if notify:
            if "notify" == notify.lower():
                notify = True
        if number > 5:
            number = 5
        now = pendulum.now()
        url = "https://calendar.google.com/calendar/ical/evkik103ah18l0q2pm7hdu1lb8%40group.calendar.google.com/public/basic.ics"
        data = requests.get(url)
        data = jicson.fromText(data.text.replace('\r', ''))
        data = data['VCALENDAR'][0]
        #print(json.dumps(data, indent=2))
        name = data['X-WR-CALNAME']
        events = data['VEVENT']
        #print(name, events)
        next_event = []
        for event in events:
            event_begin = pendulum.parse(event['DTSTART'])
            if now < event_begin:
                next_event.append(event)
        
        next_event = sorted(next_event, key=lambda kv: kv['DTSTART'])

        #next_event = next_event[]

        parsed = []
        fields_ = []
        for event in next_event[:number]:
            diff = pendulum.parse(event['DTSTART']).diff(now).in_words()
            if "seconds" in diff:
                diff = diff.split()
                diff = " ".join(diff[:-2])
            parsed.append("{} TCT: **{}** | _in {}_".format(
                pendulum.parse(event['DTSTART']).format('MM/DD HH:mm'),
                event['SUMMARY'],
                diff
            ))
            tmp = {}
            tmp['name'] = "**{}**".format(event['SUMMARY'])
            tmp['value'] = "📅 {} ⌚ _in {}_\n​".format(
               pendulum.parse(event['DTSTART']).format('MM/DD HH:mm'), diff
            )
            fields_.append(tmp)

        reply = "@everyone"

        embed = discord.Embed(
            color=3447003,
            title="Upcoming on the **{}**:".format(name),
            url="https://calendar.google.com/calendar/embed?src=evkik103ah18l0q2pm7hdu1lb8%40group.calendar.google.com"
        )
        embed = embed.set_thumbnail(url="https://www.gstatic.com/images/branding/product/2x/calendar_48dp.png")

        for item in fields_:
            embed.add_field(name=item['name'], value=item['value'])

        if notify:
            await ctx.send(reply, embed=embed)
        else:
            await ctx.send(embed=embed)
        

def setup(bot):
    bot.add_cog(Faction(bot))