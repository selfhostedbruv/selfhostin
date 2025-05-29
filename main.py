# main.py
import discord
import asyncio
from discord.ext import commands, tasks
from datetime import datetime
from flask import Flask, Response
import threading
import os
import time

# Create Flask app
app = Flask(__name__)

@app.route('/')
def index():
    return Response("Discord bot is running!", status=200, mimetype='text/plain')

@app.route('/ping')
def ping():
    return Response("Pong!", status=200, mimetype='text/plain')

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Start Flask server in background thread
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Store active tasks
message_tasks = {}

class RepeatingTask:
    def __init__(self, bot, ctx, channel, message, interval, count):
        self.bot = bot
        self.ctx = ctx
        self.channel = channel
        self.message = message
        self.interval = interval
        self.count = count
        self.current_count = 0
        self.task = None
        self.id = str(time.time()).replace('.', '')[-10:]
        self.start_time = datetime.now()
        
    async def start(self):
        self.task = self.bot.loop.create_task(self.run())
        message_tasks[self.id] = self
        
    async def run(self):
        try:
            while True:
                if self.count > 0 and self.current_count >= self.count:
                    break
                    
                await asyncio.sleep(self.interval)
                await self.channel.send(self.message)
                self.current_count += 1
                
                # Check if we should stop
                if self.count > 0 and self.current_count >= self.count:
                    break
                    
        except asyncio.CancelledError:
            pass
        finally:
            if self.id in message_tasks:
                del message_tasks[self.id]
                await self.ctx.send(f"✅ Task `{self.id}` completed!" if self.count > 0 else f"⏹️ Stopped task `{self.id}`")

    def stop(self):
        if self.task:
            self.task.cancel()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("------")
    print(f"Health check URL: http://localhost:{os.getenv('PORT', 10000)}/ping")

@bot.command()
async def repeat(ctx, interval: int, count: int, *, message: str):
    """Start repeating messages
    Example: !repeat 10 5 "Hello world"
    """
    if interval < 1:
        return await ctx.send("⛔ Interval must be at least 1 second")
    if count < 0:
        return await ctx.send("⛔ Count must be 0 or positive number")
    
    task = RepeatingTask(
        bot=bot,
        ctx=ctx,
        channel=ctx.channel,
        message=message,
        interval=interval,
        count=count
    )
    
    await task.start()
    
    await ctx.send(
        f"🚀 Started repeating message in {ctx.channel.mention}!\n"
        f"• ID: `{task.id}`\n"
        f"• Interval: {interval} seconds\n"
        f"• Repeats: {count if count > 0 else '∞'} times\n"
        f"• Message: {message}"
    )

@bot.command()
async def repeat_in(ctx, channel: discord.TextChannel, interval: int, count: int, *, message: str):
    """Start repeating messages in specific channel
    Example: !repeat_in #general 10 5 "Hello world"
    """
    if interval < 1:
        return await ctx.send("⛔ Interval must be at least 1 second")
    if count < 0:
        return await ctx.send("⛔ Count must be 0 or positive number")
    
    task = RepeatingTask(
        bot=bot,
        ctx=ctx,
        channel=channel,
        message=message,
        interval=interval,
        count=count
    )
    
    await task.start()
    
    await ctx.send(
        f"🚀 Started repeating message in {channel.mention}!\n"
        f"• ID: `{task.id}`\n"
        f"• Interval: {interval} seconds\n"
        f"• Repeats: {count if count > 0 else '∞'} times\n"
        f"• Message: {message}"
    )

@bot.command()
async def stop(ctx, task_id: str):
    """Stop a repeating task
    Example: !stop 1234567890
    """
    task = message_tasks.get(task_id)
    if task:
        task.stop()
        await ctx.send(f"⏹️ Stopped task `{task_id}`")
    else:
        await ctx.send("⚠️ Task not found. Use `!tasks` to see active tasks")

@bot.command()
async def tasks(ctx):
    """List active repeating tasks"""
    if not message_tasks:
        return await ctx.send("No active tasks")
    
    embed = discord.Embed(title="Active Repeating Tasks", color=0x00ff00)
    for task_id, task in message_tasks.items():
        status = f"Run {task.current_count}/{task.count}" if task.count > 0 else "∞ Running"
        embed.add_field(
            name=f"ID: `{task_id}`",
            value=(
                f"Channel: <#{task.channel.id}>\n"
                f"Interval: {task.interval}s\n"
                f"Status: {status}\n"
                f"Message: {task.message}\n"
                f"Started: <t:{int(task.start_time.timestamp())}:R>"
            ),
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! {latency}ms")

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("Error: DISCORD_BOT_TOKEN environment variable not set!")
        exit(1)
    bot.run(token)
