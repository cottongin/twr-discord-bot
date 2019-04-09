# import asyncio
import discord
# import aiohttp
from discord.ext import commands
import os
import requests, pendulum, pickle
import motor.motor_asyncio
from plugins.helpers import _helperFuncs as utils
from urllib.parse import quote_plus

class Weather(commands.Cog):
    """Faction information and related commands"""
    def __init__(self, bot):
        self.bot = bot
        self.key = os.getenv("WEATHER_KEY")
        self.geo = os.getenv("GEO_KEY")
        #print(os.getenv("MONGODB_URI"))
        self.client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URI"))
        self.db = self.client['db']
        #print(self.db)
        try:
            self.cached_locations, self.user_locations = self._load_cache()
        except:
            self.cached_locations = {}
            self.user_locations = {}
        print(self.cached_locations, self.user_locations)

    @commands.command(aliases=['c2f'])
    async def ctof(self, ctx, *, temp: float):
        """Converts provided Celsius temperature to Fahrenheit"""
        # (0°C × 9/5) + 32 = 32°F
        await ctx.send("**{:.1f}°F** ({:.1f}°C)".format(
            (temp * (9/5)) + 32,
            temp
        ))

    @commands.command(aliases=['f2c'])
    async def ftoc(self, ctx, *, temp: float):
        """Converts provided Fahrenheit temperature to Celsius"""
        # (0°F − 32) × 5/9 = -17.78°C
        await ctx.send("**{:.1f}°C** ({:.1f}°F)".format(
            (temp - 32) * (5/9),
            temp
        ))

    @commands.command(aliases=['w'])
    async def weather(self, ctx, *args):
        """Returns weather information for provided location. Powered by OpenCageData & DarkSky"""
        caller = str(ctx.message.author.id)
        if not args:
            if caller not in self.user_locations:
                await ctx.send("You need to give me a location!")
                return
        location = " ".join(args) or self.user_locations.get(caller)
        location = location.lower()
        # byline1 = discord.Embed(
        #     title="Powered by OSM/Nominatim",
        #     url="https://nominatim.openstreetmap.org/"
        # )
        units = {
            "uk2": {
                "temp": "C",
                "pres": "mb",
                "speed": "mph",
            },
            "us": {
                "temp": "F",
                "pres": "mb",
                "speed": "mph",
            },
            "ca": {
                "temp": "C",
                "pres": "hPa",
                "speed": "km/h",
            },
            "si": {
                "temp": "C",
                "pres": "hPa",
                "speed": "m/s",
            }
        }
        emoji = {
            "clear-day": "☀️", 
            "clear-night": "🌃",
            "rain": "🌧️",
            "snow": "❄️",
            "sleet": "🌧️/❄️", 
            "wind": "🌬️", 
            "fog": "🌫️", 
            "cloudy": "🌥️", 
            "partly-cloudy-day": "🌥️", 
            "partly-cloudy-night": "☁️",
            "hail": "", 
            "thunderstorm": "⛈️", 
            "tornado": "🌪️"
        }
        if location not in self.cached_locations:
            #print("Weather: location not cached, finding")
            lat, lon, name = self._fetch_lat_lon(location)
            #print(lat,lon,name)
            if not lat and not lon:
                await ctx.send("Error finding that location :(")
                return
            self.cached_locations[location] = (lat, lon, name)
            await self._dump_cache()
        else:
            #print("Weather: location cached, using cache")
            lat, lon, name = self.cached_locations[location]

        url = f"https://api.darksky.net/forecast/{self.key}/{lat},{lon}?units=auto"
        print(url)

        try:
            data = requests.get(url).json()
        except:
            await ctx.send("Error fetching weather! :(")
            return

        #print(data)
        def fc(temp):
            return (temp - 32) * (5/9)

        def cf(temp):
            return (temp * (9/5)) + 32

        loc_units = data['flags']['units']
        f_or_c = units[loc_units]['temp']
        if f_or_c == "F":
            # convert F to C
            conv_current_temp = "/{}°C".format(round(fc(data['currently']['temperature'])))
            conv_apparent_temp = "/{}°C".format(round(fc(data['currently']['apparentTemperature'])))
            conv_dewPoint = "/{}°C".format(round(fc(data['currently']['dewPoint'])))
        elif f_or_c == "C":
            # convert C to F
            conv_current_temp = "/{}°F".format(round(cf(data['currently']['temperature'])))
            conv_apparent_temp = "/{}°F".format(round(cf(data['currently']['apparentTemperature'])))
            conv_dewPoint = "/{}°F".format(round(cf(data['currently']['dewPoint'])))
        else:
            conv_current_temp = ""
            conv_apparent_temp = ""
            conv_dewPoint = ""
        title = f"**{name}**"
        tz = data['timezone']
        #updated = "As of: {}".format(pendulum.from_timestamp(data['currently']['time'], tz=tz).format("MMM Do HH:mm zz"))
        current = "**{}°{}{}** (feels like {}°{}{}) | {} {}".format(
            round(data['currently']['temperature']),
            units[loc_units]['temp'],
            conv_current_temp,
            round(data['currently']['apparentTemperature']),
            units[loc_units]['temp'],
            conv_apparent_temp,
            data['currently']['summary'],
            emoji.get(data['currently']['icon']) or "",
        )

        details = "{:.0%} humidity (dew point {}°{}{}) | Pressure: {} {} | {} {} winds gusting to {} {} from the {}".format(
            round(data['currently']['humidity'], 2),
            round(data['currently']['dewPoint']),
            units[loc_units]['temp'],
            conv_dewPoint,
            round(data['currently']['pressure']),
            units[loc_units]['pres'],
            round(data['currently']['windSpeed']),
            units[loc_units]['speed'],
            round(data['currently']['windGust']),
            units[loc_units]['speed'],
            self._compass(data['currently']['windBearing'])
        )

        fc_strings = []
        for day in data['daily']['data'][:5]:
            day_str = utils.bold(pendulum.from_timestamp(day['time'], tz=tz).format("ddd"))
            high = round(day['temperatureHigh'])
            low = round(day['temperatureLow'])
            icon = emoji.get(day['icon']) or ""
            if icon: icon = "{} ".format(icon)
            if f_or_c == "F":
                conv_high = round(fc(day['temperatureHigh']))
                conv_low = round(fc(day['temperatureLow']))
                conv = " (️️️️️↑{}C ↓{}C)".format(conv_high, conv_low)
            elif f_or_c == "C":
                conv_high = round(cf(day['temperatureHigh']))
                conv_low = round(cf(day['temperatureLow']))
                conv = " ️(↑{}F ↓{}F)".format(conv_high, conv_low)
            else:
                conv = ""
            total = f"{day_str}: {icon}**↑{high}{f_or_c} ↓{low}{f_or_c}**{conv}"
            fc_strings.append(total)

        try:
            hourly = "{}\n".format(data['minutely']['summary'])
        except:
            hourly = ""
        
        # forecast = "**Forecast**\t{}\n{}**Today:** {}\n**Week ahead:** {}".format(
        #     " ".join(fc_strings),
        #     hourly,
        #     data['hourly']['summary'],
        #     data['daily']['summary']
        # )

        # lines = [
        #     current,
        #     details,
        #     forecast,
        # ]

        #reply = "\n".join(lines)

        #reply = "@everyone"

        byline2 = discord.Embed(
            color=3447003,
            title=title,
            url='https://darksky.net/forecast/%s,%s' % (lat, lon),
        )
        #byline2.set_author(name="Dark Sky", url="https://darksky.net/poweredby/", icon_url="https://darksky.net/dev/img/attribution/poweredby-darkbackground.png")
        #byline2.set_thumbnail(url="https://darksky.net/dev/img/attribution/poweredby-darkbackground.png")
        byline2.add_field(name="**Currently**", value=current)
        byline2.add_field(name="**Details**", value=details)
        if hourly: byline2.add_field(name="**Now**", value=hourly)
        byline2.add_field(name="**Forecast**", value="\n".join(fc_strings))
        byline2.add_field(name="**Today**", value=data['hourly']['summary'])
        byline2.add_field(name="**Week ahead**", value=data['daily']['summary'])
        byline2.set_footer(text="Powered by Dark Sky", icon_url="https://darksky.net/dev/img/attribution/poweredby-darkbackground.png")

        # embed = discord.Embed(
        #     color=3447003,
        #     title="Upcoming on the **{}**:".format(name),
        #     url="https://calendar.google.com/calendar/embed?src=evkik103ah18l0q2pm7hdu1lb8%40group.calendar.google.com"
        # )
        # embed = embed.set_thumbnail(url="https://www.gstatic.com/images/branding/product/2x/calendar_48dp.png")

        # for item in fields_:
        #     embed.add_field(name=item['name'], value=item['value'])

        # if notify:
        #     await ctx.send(reply, embed=embed)
        # else:
        #     await ctx.send(embed=embed)

        await ctx.send(embed=byline2)
        #if caller in self.user_locations:
        self.user_locations[caller] = location
        await self._dump_user_cache()
        #await ctx.send(embed=byline1)
        #await ctx.send(embed=byline2)

    def _compass(self, bearing):
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        ix = int((bearing + 11.25)/22.5)
        return dirs[ix % 16]


    def _fetch_lat_lon(self, location):
        location_u = quote_plus(location)
        
        # if location.isdigit() and len(location) == 5:
        #     location_u = "postalcode={}".format(location_u)
        #     ap = "&countrycodes=us"
        # elif location.isalnum():
        #     location_u = "postalcode={}".format(location_u)
        #     ap = "&countrycodes=ca"
        # else:
        #     location_u = "q={}".format(location_u)
        #     ap = ""
        url = f"https://api.opencagedata.com/geocode/v1/json?key={self.geo}&q={location_u}&no_annotations=1&abbrv=1&limit=1"
        #print(url)
        try:
            data = requests.get(url).json()
        except:
            return None, None, None
        if not data:
            return None, None, None
        lat = data['results'][0]['geometry']['lat']
        lon = data['results'][0]['geometry']['lng']
        name = data['results'][0]['formatted']
        return lat, lon, name

    def _load_cache(self):
        b = await self.db.user_cache.find_one()
        c = await self.db.weather_locations.find_one()
        return b,c

    async def _dump_cache(self):
        c = await self.db.weather_locations.find_one()
        if c:
            await self.db.weather_locations.replace_one({'_id': c['_id']}, self.cached_locations)
        else:
            await self.db.weather_locations.insert_one(self.cached_locations)

    async def _dump_user_cache(self):
        c = await self.db.user_cache.find_one()
        if c:
            await self.db.user_cache.replace_one({'_id': c['_id']}, self.user_locations)
        else:
            await self.db.user_cache.insert_one(self.user_locations)

def setup(bot):
    bot.add_cog(Weather(bot))