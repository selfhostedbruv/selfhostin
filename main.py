# main.py
import discord
import asyncio
from discord.ext import commands, tasks
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

message_tasks = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("------")

def create_task_id():
    return str(datetime.now().timestamp()).replace('.', '')[-10:]

async def send_repeated_messages(ctx, message, interval, count, channel):
    task_id = create_task_id()
    
    @tasks.loop(seconds=interval, count=count)
    async def message_task():
        await channel.send(message)
        if message_task.current_loop == count - 1:
            del message_tasks[task_id]
            await ctx.send(f"✅ Task `{task_id}` completed!")

    message_tasks[task_id] = message_task
    message_task.start()
    
    await ctx.send(
        f"🚀 Started repeating message in {channel.mention}!\n"
        f"• ID: `{task_id}`\n"
        f"• Interval: {interval} seconds\n"
        f"• Repeats: {count if count > 0 else '∞'} times\n"
        f"• Message: {message}"
    )

@bot.command()
async def repeat(ctx, interval: int, count: int, *, message: str):
    """Start repeating messages
    Example: !repeat 10 5 "Hello world"
    """
    if interval < 1:
        return await ctx.send("⛔ Interval must be at least 1 second")
    if count < 0:
        return await ctx.send("⛔ Count must be 0 or positive number")
    
    await send_repeated_messages(ctx, message, interval, count, ctx.channel)

@bot.command()
async def repeat_in(ctx, channel: discord.TextChannel, interval: int, count: int, *, message: str):
    """Start repeating messages in specific channel
    Example: !repeat_in #general 10 5 "Hello world"
    """
    if interval < 1:
        return await ctx.send("⛔ Interval must be at least 1 second")
    if count < 0:
        return await ctx.send("⛔ Count must be 0 or positive number")
    
    await send_repeated_messages(ctx, message, interval, count, channel)

@bot.command()
async def stop(ctx, task_id: str):
    """Stop a repeating task
    Example: !stop 1234567890
    """
    task = message_tasks.get(task_id)
    if task:
        task.cancel()
        del message_tasks[task_id]
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
        status = f"Running {task.current_loop}/{task.count}" if task.count else "Running forever"
        embed.add_field(
            name=f"ID: `{task_id}`",
            value=(
                f"Channel: <#{task.channel.id}>\n"
                f"Interval: {task.seconds}s\n"
                f"Status: {status}\n"
                f"Message: {task.message}"
            ),
            inline=False
        )
    await ctx.send(embed=embed)

if __name__ == "__main__":
    import os
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))

import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Discord bot is running!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
