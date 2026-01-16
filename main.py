import discord
from discord.ext import commands
import yt_dlp
import asyncio
import requests
import os
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
# টোকেনটি হাইড করা হয়েছে (Render Environment এ DISCORD_TOKEN নাম দিয়ে টোকেনটি বসাবেন)
TOKEN = os.environ.get('DISCORD_TOKEN')
# ওয়েব হুক ইউআরএলটি আপনার অনুরোধ অনুযায়ী সরাসরি রাখা হলো
WEBHOOK_URL = 'https://discord.com/api/webhooks/1461571981211074736/HfJEgfjBMZGIuvdb-buBECGQ92hRnwNCKpRegrMHoYYKNNdg5XFAczz8wfdxTHLqxqVp'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='m!', intents=intents)

# Music Options - উন্নত ইউটিউব সাপোর্ট এবং রি-কানেক্ট সেটিংস
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

queue = []

# --- KEEP ALIVE SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home():
    return "<h1>BENJA MUSIC IS ONLINE!</h1>"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- WEBHOOK LOGS ---
def send_logs(action, title, url):
    payload = {
        "embeds": [{
            "title": f"🚀 SYSTEM LOGS - {action}",
            "description": f"✨ **Track:** {title}\n🔗 **URL:** {url}",
            "color": 0x1DB954,
            "footer": {"text": "DEVELOPED BY TALHA | PREMIUM LOGS"}
        }]
    }
    try:
        requests.post(WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Webhook Error: {e}")

@bot.event
async def on_ready():
    print(f'>>> {bot.user.name} IS NOW ONLINE <<<')
    # বটের স্ট্যাটাসে গান শোনার টেক্সট যোগ করা হয়েছে
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name="m!play")
    )

# --- COMMANDS ---

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()
        embed = discord.Embed(
            description=f"🎧 Joined **{channel}** successfully! ✨", 
            color=0x3498db
        )
        embed.set_footer(text="DEVELOPED BY TALHA")
        await ctx.send(embed=embed)
        return True
    else:
        embed = discord.Embed(
            title="Access Denied!",
            description="⚠️ You must be in a **Voice Channel** to use this command!", 
            color=0xff4757
        )
        embed.set_footer(text="DEVELOPED BY TALHA")
        await ctx.send(embed=embed)
        return False

@bot.command()
async def play(ctx, *, search):
    # ইউজার VC-তে আছে কি না চেক (একবার ওয়ার্নিং দেওয়ার জন্য)
    if not ctx.author.voice:
        embed = discord.Embed(
            title="Access Denied!",
            description="⚠️ You must be in a **Voice Channel** to play music!", 
            color=0xff4757
        )
        embed.set_footer(text="DEVELOPED BY TALHA")
        return await ctx.send(embed=embed)

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    async with ctx.typing():
        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
                url, title, web_url = info['url'], info['title'], info['webpage_url']
                thumbnail = info.get('thumbnail')

            source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            
            if ctx.voice_client.is_playing():
                queue.append({'source': source, 'title': title, 'url': web_url, 'thumbnail': thumbnail})
                embed = discord.Embed(
                    title="⌛ Added to Queue", 
                    description=f"**[{title}]({web_url})**", 
                    color=0xe67e22
                )
                embed.set_footer(text="DEVELOPED BY TALHA")
                await ctx.send(embed=embed)
            else:
                ctx.voice_client.play(source, after=lambda e: bot.loop.create_task(play_next(ctx)))
                embed = discord.Embed(
                    title="🎶 Now Playing", 
                    description=f"**[{title}]({web_url})**", 
                    color=0x2ecc71
                )
                if thumbnail:
                    embed.set_thumbnail(url=thumbnail)
                embed.set_footer(text="DEVELOPED BY TALHA | PREMIUM EXPERIENCE")
                await ctx.send(embed=embed)
                send_logs("PLAYING", title, web_url)
        except Exception as e:
            await ctx.send(f"❌ **Error:** গানের তথ্য আনা সম্ভব হচ্ছে না। ইউটিউব বট চেক করছে।\n`{str(e)[:150]}`")

async def play_next(ctx):
    if len(queue) > 0:
        next_song = queue.pop(0)
        ctx.voice_client.play(next_song['source'], after=lambda e: bot.loop.create_task(play_next(ctx)))
        
        embed = discord.Embed(
            title="⏭ Auto-Playing Next Track", 
            description=f"**[{next_song['title']}]({next_song['url']})**", 
            color=0x2ecc71
        )
        if next_song['thumbnail']:
            embed.set_thumbnail(url=next_song['thumbnail'])
        embed.set_footer(text="DEVELOPED BY TALHA")
        await ctx.send(embed=embed)
        send_logs("AUTO PLAY", next_song['title'], next_song['url'])
    else:
        # ৩ মিনিট গান না চললে ডিসকানেক্ট হবে
        await asyncio.sleep(180)
        if not ctx.voice_client.is_playing() and not queue:
            await ctx.voice_client.disconnect()

@bot.command()
async def skip(ctx):
    if not ctx.author.voice:
        return await ctx.send("⚠️ You must be in the VC to skip music!")
    
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        embed = discord.Embed(
            description="⏭️ **Track Skipped!** Moving to the next song...", 
            color=0x3498db
        )
        embed.set_footer(text="DEVELOPED BY TALHA")
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Nothing is playing to skip!")

@bot.command()
async def stop(ctx):
    if not ctx.author.voice:
        return await ctx.send("⚠️ You must be in the VC to stop music!")

    if not ctx.voice_client or not ctx.voice_client.is_playing():
        return await ctx.send("⚠️ No music is currently playing!")

    ctx.voice_client.stop()
    queue.clear()
    embed = discord.Embed(
        description="🛑 **Playback Stopped.** The queue has been cleared!", 
        color=0xe74c3c
    )
    embed.set_footer(text="DEVELOPED BY TALHA")
    await ctx.send(embed=embed)

@bot.command()
async def leave(ctx):
    if not ctx.author.voice:
        return await ctx.send("⚠️ You must be in the VC to use this!")

    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        embed = discord.Embed(
            title="👋 Goodbye & See You Soon!", 
            description="Thank you for choosing **BENJA MUSIC**. I hope you enjoyed the session!\n\n*Feel free to invite me back anytime.*", 
            color=0x5865F2
        )
        embed.add_field(name="Session Status", value="✅ Disconnected Successfully", inline=True)
        embed.add_field(name="Developer", value="💎 Talha", inline=True)
        embed.set_footer(text="DEVELOPED BY TALHA | PREMIUM EXPERIENCE")
        await ctx.send(embed=embed)

if __name__ == '__main__':
    keep_alive()
    bot.run(TOKEN)
