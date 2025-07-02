
import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

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
    1380573604345020568,  # 🎯 Role Founder
    1384509515289854012,  # 🎯 Role Senior admin
    784460584921727014,  # 🎯 Role Admin
    866982651684585522,  # 🎯 Role Mod
    832892308637876244,  # 🎯 Role Helper
]
ALLOWED_CHANNEL_ID = 1389823355787411516    # 👈 ID kênh mà người thường được dùng
FORUM_CHANNEL_ID = 1389430767217676368      # 👈 ID forum channel để xếp hạng

@bot.event
async def on_ready():
    print(f"✅ Bot đã sẵn sàng: {bot.user}")

@bot.command(name="topreaction")
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

            for reaction in first_msg.reactions:
                users = [user async for user in reaction.users()]
                for user in users:
                    if not user.bot and (now - user.created_at) >= one_month:
                        total_reacts += 1

            result.append((thread, total_reacts))

        except Exception as e:
            print(f"❌ Lỗi ở thread {thread.name}: {e}")
            continue

    if not result:
        await ctx.send("⚠️ Không có bài viết nào đủ điều kiện.")
        return

    result.sort(key=lambda x: x[1], reverse=True)

    response = "**📊 Top bài viết theo reaction đầu tiên (lọc acc mới, hiển thị người tạo):**\n"
    for i, (thread, count) in enumerate(result[:10], start=1):
        creator = thread.owner or ctx.guild.get_member(thread.owner_id)
        display_name = creator.display_name if creator else "Không rõ"
        response += f"**#{i}** – [{display_name}]({thread.jump_url}) với **{count}** reaction\n"

    await ctx.send(response)

bot.run(TOKEN)
