import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os
from discord.ui import View, Button

# Load .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# INTENTS
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === CẤU HÌNH WHITELIST + CHANNEL GIỚI HẠN ===
WHITELIST_ROLE_IDS = [
    1380573604345020568,
    1384509515289854012,
    1384509462512930868,
    784460584921727014,
    866982651684585522,
    832892308637876244,
]
ALLOWED_CHANNEL_ID = 1389823355787411516
FORUM_CHANNEL_ID = 1389430767217676368


@bot.event
async def on_ready():
    print(f"✅ Bot đã sẵn sàng: {bot.user}")

@bot.command(name="atopvote")
async def top_reaction(ctx):
    author = ctx.author
    channel = ctx.channel

    is_whitelisted = any(role.id in WHITELIST_ROLE_IDS for role in author.roles)

    if not is_whitelisted and channel.id != ALLOWED_CHANNEL_ID:
        channel_mention = bot.get_channel(ALLOWED_CHANNEL_ID).mention
        await ctx.send(f"🚫 Bạn chỉ có thể dùng lệnh này ở {channel_mention}.")
        return

    forum_channel = bot.get_channel(FORUM_CHANNEL_ID)
    print(f"🔍 Bot thấy được channel: {forum_channel}")

    if not isinstance(forum_channel, discord.ForumChannel):
        await ctx.send("❌ Không tìm thấy forum channel hợp lệ.")
        return

    try:
        archived_threads = [t async for t in forum_channel.archived_threads()]
    except Exception as e:
        print(f"⚠️ Lỗi khi lấy archived threads: {e}")
        archived_threads = []

    active_threads = forum_channel.threads
    all_threads = active_threads + archived_threads

    result = []
    now = datetime.now(timezone.utc)
    one_month = timedelta(days=30)

    for thread in all_threads:
        try:
            messages = [msg async for msg in thread.history(limit=1, oldest_first=True)]
            if not messages:
                continue

            first_msg = messages[0]
            total_reacts = 0

            if first_msg.reactions:
                first_reaction = first_msg.reactions[0]
                users = [user async for user in first_reaction.users()]
                for user in users:
                    if not user.bot and (now - user.created_at) >= one_month:
                        total_reacts += 1

            # Đếm số lượng reaction không hợp lệ (dưới 1 tháng)
            invalid_reacts = 0
            for reaction in first_msg.reactions:
                users = [user async for user in reaction.users()]
                for user in users:
                    if not user.bot and (now - user.created_at) < one_month:
                        invalid_reacts += 1
            result.append((thread, total_reacts, invalid_reacts))

        except Exception as e:
            print(f"❌ Lỗi ở thread {thread.name}: {e}")
            continue

    if not result:
        await ctx.send("⚠️ Không có bài viết nào đủ điều kiện.")
        return

    result.sort(key=lambda x: x[1], reverse=True)

    total_invalid_users = sum(invalid for _, _, invalid in result)

    response = "**📊 Top bài viết theo reaction đầu tiên (lọc acc mới, hiển thị người tạo):**\n"
    for i, (thread, count, invalid) in enumerate(result[:10], start=1):
        creator = thread.owner or ctx.guild.get_member(thread.owner_id)
        display_name = creator.display_name if creator else "Không rõ"

        line = f"**#{i}** – [{display_name}]({thread.jump_url}) với **{count}** reaction"
        if invalid > 0:
            line += f" (**{invalid} reaction không đủ điều kiện**)"
        response += line + "\n"

    await ctx.send(response)

@bot.command(name="invalidvoters")
async def invalid_voters(ctx):
    forum_channel = bot.get_channel(FORUM_CHANNEL_ID)
    author = ctx.author
    channel = ctx.channel
    
    is_whitelisted = any(role.id in WHITELIST_ROLE_IDS for role in author.roles)

    if not is_whitelisted and channel.id != ALLOWED_CHANNEL_ID:
        channel_mention = bot.get_channel(ALLOWED_CHANNEL_ID).mention
        await ctx.send(f"🚫 Bạn chỉ có thể dùng lệnh này ở {channel_mention}.")
        return

    if not isinstance(forum_channel, discord.ForumChannel):
        await ctx.send("❌ Không tìm thấy forum channel hợp lệ.")
        return

    try:
        archived_threads = [t async for t in forum_channel.archived_threads()]
    except Exception as e:
        print(f"⚠️ Lỗi khi lấy archived threads: {e}")
        archived_threads = []

    active_threads = forum_channel.threads
    all_threads = active_threads + archived_threads

    now = datetime.now(timezone.utc)
    one_month = timedelta(days=30)
    invalid_user_threads = {}

    for thread in all_threads:
        try:
            messages = [msg async for msg in thread.history(limit=1, oldest_first=True)]
            if not messages:
                continue

            first_msg = messages[0]

            for reaction in first_msg.reactions:
                users = [user async for user in reaction.users()]
                for user in users:
                    if user.bot:
                        continue
                    account_age = now - user.created_at
                    if account_age < one_month:
                        key = f"{user.name}#{user.discriminator} (tạo {user.created_at.date()})"
                        if key not in invalid_user_threads:
                            invalid_user_threads[key] = []
                        invalid_user_threads[key].append(f"[{thread.name}]({thread.jump_url})")
        except Exception as e:
            print(f"❌ Lỗi ở thread {thread.name}: {e}")
            continue

    if not invalid_user_threads:
        await ctx.send("🎉 Không có người dùng nào dưới 1 tháng đã reaction.")
        return

    usernames = list(invalid_user_threads.keys())
    embeds = []

    for username in usernames:
        description = ", ".join(invalid_user_threads[username])
        embed = discord.Embed(
            title=f"👶 {username}",
            description=description,
            color=discord.Color.orange()
        )
        embeds.append(embed)

    class InvalidVoterView(View):
        def __init__(self):
            super().__init__(timeout=30)
            self.index = 0

        @discord.ui.button(label="◀️ Trước", style=discord.ButtonStyle.secondary)
        async def prev(self, interaction: discord.Interaction, button: Button):
            self.index = (self.index - 1) % len(embeds)
            await interaction.response.edit_message(embed=embeds[self.index], view=self)

        @discord.ui.button(label="▶️ Sau", style=discord.ButtonStyle.secondary)
        async def next(self, interaction: discord.Interaction, button: Button):
            self.index = (self.index + 1) % len(embeds)
            await interaction.response.edit_message(embed=embeds[self.index], view=self)

    await ctx.send(embed=embeds[0], view=InvalidVoterView())


bot.run(TOKEN)
