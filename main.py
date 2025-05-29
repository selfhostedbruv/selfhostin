# main.py
import discord
import asyncio
from discord.ext import commands
from datetime import datetime
from flask import Flask, Response
import threading
import os
import time

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

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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
                if self.count > 0:
                    await self.ctx.send(f"✅ Task `{self.id}` completed!")
                else:
                    await self.ctx.send(f"⏹️ Stopped task `{self.id}`")

    def stop(self):
        if self.task:
            self.task.cancel()

def is_admin():
    """Check if user has Administrator permissions"""
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        await ctx.send("⛔ You need Administrator permissions to use this bot!")
        return False
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("------")
    print(f"Health check URL: http://localhost:{os.getenv('PORT', 10000)}/ping")

@bot.command()
@is_admin()
async def repeat(ctx, interval: int, count: int, *, message: str):
    """Start repeating messages (Admin only)"""
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
@is_admin()
async def repeat_in(ctx, channel: discord.TextChannel, interval: int, count: int, *, message: str):
    """Start repeating messages in specific channel (Admin only)"""
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
@is_admin()
async def stop(ctx, task_id: str):
    """Stop a repeating task (Admin only)"""
    task = message_tasks.get(task_id)
    if task:
        task.stop()
        await ctx.send(f"⏹️ Stopped task `{task_id}`")
    else:
        await ctx.send("⚠️ Task not found. Use `!tasks` to see active tasks")

@bot.command()
@is_admin()
async def tasks(ctx):
    """List active repeating tasks (Admin only)"""
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

@bot.command()
@is_admin()
async def adminhelp(ctx):
    """Show admin commands help"""
    embed = discord.Embed(title="Admin Bot Commands", color=0x3498db)
    embed.add_field(
        name="!repeat [seconds] [count] [message]",
        value="Start repeating messages in current channel\n"
              "Example: `!repeat 10 5 \"Hello world\"`",
        inline=False
    )
    embed.add_field(
        name="!repeat_in [#channel] [seconds] [count] [message]",
        value="Start repeating messages in specific channel\n"
              "Example: `!repeat_in #announcements 3600 0 \"Hourly update\"`",
        inline=False
    )
    embed.add_field(
        name="!stop [task_id]",
        value="Stop a repeating task\n"
              "Example: `!stop 1234567890`",
        inline=False
    )
    embed.add_field(
        name="!tasks",
        value="List all active repeating tasks",
        inline=False
    )
    embed.add_field(
        name="!adminhelp",
        value="Show this help message",
        inline=False
    )
    embed.set_footer(text="Requires Administrator permissions")
    await ctx.send(embed=embed)

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("Error: DISCORD_BOT_TOKEN environment variable not set!")
        exit(1)
    bot.run(token)
