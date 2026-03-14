import discord
from discord.ext import commands
import asyncio
import os

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- TOKEN ----------------
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is not set")

# ---------------- CONFIG ----------------
fto_role_id = 1479648729362333697   # Field Training Officer
REQUEST_CHANNEL_NAME = "request-ride-along"

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ---------------- COMMAND ----------------
@bot.command()
async def ra(ctx):
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass

    if not isinstance(ctx.channel, discord.TextChannel):
        return

    dm = await ctx.author.create_dm()

    # ---- Question 1: Type ----
    dm_embed = discord.Embed(
        title="Ride-Along Request",
        description=(
            "What type of ride-along are you requesting?\n\n"
            "1️⃣ Day 1 ride-along\n"
            "2️⃣ Day 2 ride-along\n"
            "3️⃣ Day 3 ride-along\n"
            "4️⃣ Day 4 Evaluation ride-along\n\n"
            "Type **1**, **2**, **3**, or **4**."
        ),
        color=discord.Color.green()
    )
    await dm.send(embed=dm_embed)

    def type_check(m):
        return m.author == ctx.author and m.channel == dm and m.content in {"1", "2", "3", "4"}

    try:
        msg = await bot.wait_for("message", check=type_check, timeout=60)
    except asyncio.TimeoutError:
        await dm.send(embed=discord.Embed(
            title="Ride-Along Request Timeout",
            description="You took too long to respond. Please try again.",
            color=discord.Color.red()
        ))
        return

    ride_types = {
        "1": "Day 1 ride-along",
        "2": "Day 2 ride-along",
        "3": "Day 3 ride-along",
        "4": "Day 4 Evaluation ride-along"
    }
    ride_type = ride_types[msg.content]

    await dm.send(embed=discord.Embed(
        title="Ride-Along Selection",
        description=f"You selected: **{ride_type}**",
        color=discord.Color.blue()
    ))

    # ---- Question 2: Availability ----
    time_embed = discord.Embed(
        title="Availability",
        description=(
            "What time are you available for this ride-along?\n\n"
            "Example: `Tonight 9pm–11pm EST` or `Jan 14 @ 6pm EST`.\n\n"
            "Type your availability below."
        ),
        color=discord.Color.green()
    )
    await dm.send(embed=time_embed)

    def time_check(m):
        return m.author == ctx.author and m.channel == dm and len(m.content.strip()) > 0

    try:
        time_msg = await bot.wait_for("message", check=time_check, timeout=120)
    except asyncio.TimeoutError:
        await dm.send(embed=discord.Embed(
            title="Availability Timeout",
            description="You took too long to respond. Please try again.",
            color=discord.Color.red()
        ))
        return

    availability = time_msg.content.strip()

    # ---- Channel Post ----
    role_id = fto_role_id

    embed = discord.Embed(title="Ride-Along Request", color=discord.Color.blue())
    embed.add_field(name="Requester", value=ctx.author.mention, inline=False)
    embed.add_field(name="Type", value=ride_type, inline=False)
    embed.add_field(name="Availability", value=availability, inline=False)
    embed.set_footer(text=f"requester_id:{ctx.author.id} | expires in 3 hours")

    channel = discord.utils.get(ctx.guild.text_channels, name=REQUEST_CHANNEL_NAME)
    if not channel:
        await dm.send("⚠️ Could not find the request channel.")
        return

    request_msg = await channel.send(f"<@&{role_id}>", embed=embed)
    await request_msg.add_reaction("✅")

    # Halfway reminder
    await asyncio.sleep(5400)
    await dm.send(embed=discord.Embed(
        title="Ride-Along Reminder",
        description="⏰ Your ride-along request will expire in 1.5 hours.",
        color=discord.Color.orange()
    ))

    # Expire
    await asyncio.sleep(5400)
    try:
        await request_msg.delete()
    except discord.NotFound:
        pass

# ---------------- REACTION HANDLER ----------------
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    if str(payload.emoji) != "✅":
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel or channel.name != REQUEST_CHANNEL_NAME:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.NotFound:
        return

    if not message.embeds:
        return

    embed = message.embeds[0]
    footer = embed.footer.text if embed.footer else ""

    if not footer.startswith("requester_id:"):
        return

    try:
        requester_id = int(footer.split("requester_id:")[1].split("|")[0].strip())
    except (IndexError, ValueError):
        return

    member = guild.get_member(requester_id)
    if not member:
        return

    await member.send(embed=discord.Embed(
        title="Ride-Along Accepted",
        description="✅ A Field Training Officer has accepted your ride-along request.",
        color=discord.Color.green()
    ))

# ---------------- RUN ----------------
bot.run(TOKEN)