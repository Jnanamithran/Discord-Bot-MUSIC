import discord
from discord.ext import commands
import yt_dlp
import asyncio

bot = commands.Bot(command_prefix=None, intents=discord.Intents.default())

class YTDLSource(discord.PCMVolumeTransformer):
    YDL_OPTIONS = {
        'format': 'bestaudio',
        'noplaylist': True,
        'source_address': '0.0.0.0',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True  # Skip download to stream directly
    }

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(cls.YDL_OPTIONS) as ydl:
            try:
                data = await loop.run_in_executor(None, ydl.extract_info, url)
                if 'entries' in data:
                    data = data['entries'][0]  # Use the first entry if it's a playlist

                # Use the streamable URL directly
                return cls(
                    discord.FFmpegPCMAudio(
                        data['url'],
                        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
                    ),
                    data=data
                )
            except Exception as e:
                print(f"Error in YTDLSource.from_url: {e}")
                raise

queue = []

@bot.tree.command(name="join", description="Bot joins the voice channel.")
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client is None:
            await channel.connect()
            await interaction.response.send_message("Joined the voice channel!")
        else:
            await interaction.response.send_message("I'm already in a voice channel.", ephemeral=True)
    else:
        await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)

@bot.tree.command(name="play", description="Play a song from a URL")
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    if interaction.guild.voice_client is None:
        if interaction.user.voice:
            await interaction.user.voice.channel.connect()
        else:
            await interaction.followup.send("You need to be in a voice channel to use this command.", ephemeral=True)
            return

    queue.append(url)
    if interaction.guild.voice_client.is_playing():
        await interaction.followup.send(f'Added to queue: {url}')
    else:
        await play_next(interaction)

async def play_next(interaction: discord.Interaction):
    if queue:
        url = queue.pop(0)
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop)
            interaction.guild.voice_client.play(
                player,
                after=lambda e: asyncio.run_coroutine_threadsafe(after_play(interaction), bot.loop) if e is None else print(f"Playback error: {e}")
            )
            await interaction.followup.send(f'Now playing: {player.title}')
        except Exception as e:
            print(f"Error occurred during play_next: {e}")
            await interaction.followup.send(f'Error occurred: {str(e)}')
            await play_next(interaction)  # Continue with the next song if error occurs
    else:
        print("Queue is empty.")
        await interaction.followup.send("Queue is empty.")

async def after_play(interaction: discord.Interaction):
    await asyncio.sleep(1)
    await play_next(interaction)

# /skip command to skip the current song
@bot.tree.command(name="skip", description="Skip the current song.")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()  # This will trigger the after callback to play the next song
        await interaction.response.send_message("Skipped the current song.")
    else:
        await interaction.response.send_message("No music is playing to skip.", ephemeral=True)

# /leave command to disconnect the bot from the voice channel
@bot.tree.command(name="leave", description="Disconnect from the voice channel.")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message("Disconnected from the voice channel.")
    else:
        await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)


#===============================================================================================================

# Define a slash command (e.g., `/hello`)
@bot.tree.command(name="hello", description="Say hello!")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello!")

@bot.tree.command(name="news", description="Get the latest news.")
async def news(interaction: discord.Interaction):
    await interaction.response.send_message("Latest News is available at [Google News] (https://news.google.com/home?hl=en-IN&gl=IN&ceid=IN:en)")


@bot.tree.command(name="help", description="Show available commands.")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message("Available commands:/play,/skip,/join,/leave,stop,/hello, /userinfo, /news, etc.")

@bot.tree.command(name="userinfo", description="Get info about a user.")
async def userinfo(interaction: discord.Interaction, user: discord.User = None):
    user = user or interaction.user
    await interaction.response.send_message(f"Username: {user.name}\nID: {user.id}\nJoined at: {user.joined_at}")

# Sync commands with Discord
@bot.event
async def on_ready():
    await bot.tree.sync()
    await bot.change_presence(status=discord.Status.dnd,activity=discord.Game(name="Valorant"))
    # Specify the channel ID where you want to send the message
    channel = bot.get_channel(1299786195576033381)  # Replace YOUR_CHANNEL_ID with the actual channel ID
    if channel:
        await channel.send("Bot is now online!")  # Send a message to the specified channel
    print(f'Logged in as {bot.user}')    

if __name__ == "__main__":
    token = input("Please enter your bot token: ")  # Prompt for the token
    bot.run(token)  # Run the bot with the provided token
