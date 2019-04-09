import discord
from discord.ext import commands

import os
import requests, pendulum, pickle
import redis

from plugins.helpers import _helperFuncs as utils
from urllib.parse import quote_plus

class Weather(commands.Cog):
    """Faction information and related commands"""
    def __init__(self, bot):
        self.bot = bot
        self.key = os.getenv("WEATHER_KEY")
        self.geo = os.getenv("GEO_KEY")
        self.db = redis.from_url(os.environ.get("REDIS_URL"))
        try:
            self.cached_locations, self.user_locations = self._load_cache()
        except:
            self.cached_locations = {}
            self.user_locations = {}

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
            lat, lon, name = self._fetch_lat_lon(location)
            if not lat and not lon:
                await ctx.send("Error finding that location :(")
                return
            self.cached_locations[location] = (lat, lon, name)
            self._dump_cache()
        else:
            lat, lon, name = self.cached_locations[location]

        url = f"https://api.darksky.net/forecast/{self.key}/{lat},{lon}?units=auto"

        try:
            data = requests.get(url).json()
        except:
            await ctx.send("Error fetching weather! :(")
            return

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

        await ctx.send(embed=byline2)
        self.user_locations[caller] = location
        self._dump_user_cache()

    @commands.command()
    @commands.is_owner()
    async def flushcaches(self, ctx):
        """Flushes databases"""
        self.db.set("weather_cache", "")
        self.db.set("user_cache", "")
        await ctx.send("Done")

    def _compass(self, bearing):
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        ix = int((bearing + 11.25)/22.5)
        return dirs[ix % 16]


    def _fetch_lat_lon(self, location):
        location_u = quote_plus(location)
        
        url = f"https://api.opencagedata.com/geocode/v1/json?key={self.geo}&q={location_u}&no_annotations=1&abbrv=1&limit=1"
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
        c = self.db.get("user_cache")
        b = self.db.get("weather_cache")
        b = pickle.loads(b)
        c = pickle.loads(c)
        return b,c

    def _dump_cache(self):
        tmp_c = pickle.dumps(self.cached_locations, protocol=pickle.HIGHEST_PROTOCOL)
        self.db.set("weather_cache", tmp_c)

    def _dump_user_cache(self):
        tmp_l = pickle.dumps(self.user_locations, protocol=pickle.HIGHEST_PROTOCOL)
        self.db.set("user_cache", tmp_l)

def setup(bot):
    bot.add_cog(Weather(bot))