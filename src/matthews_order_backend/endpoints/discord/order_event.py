import discord


class OrderDiscordClient(discord.Client):

    async def on_ready(self):
        print(f'We have logged in as {self.user}')

    async def on_message(self, message):

        if message.author == self.user:
            return

        if message.content.startswith('!'):
            await message.channel.send('Hello World!')
