import requests
import discord
import asyncio
import sqlite3
import json
import re
from collections import *
import datetime
from dataclasses import *
from dateutil import tz
import threading
import base64
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.environ['TOKEN'] 
DB_FILE = os.environ['DB_FILE']
EMOJI_REGEX = r'<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>'
EMOJI_REGEX_COMPILED = re.compile(EMOJI_REGEX)

print('Token is', TOKEN)
print('Db file is', DB_FILE)

if not TOKEN or not DB_FILE:
	exit(0)

"""
emotes look like this <a:peepoSnowmanDance:784039476003209217>
"""

@dataclass
class Emote:
	name: str
	id: int
	animated: any
	def __hash__(self):
		return hash((self.name, self.id))

class MyClient(discord.Client):
	def __init__(self, conn, *args, **kwargs):
		super().__init__(**kwargs)
		self.conn = conn
		#author_id
		self.authors = set()
		#emote_id: row id
		self.emotes = {}
		#self.lock = lock

	def my_run(self, token):
		self.run(token)

	def get_last_scanned(self):
		c = self.conn.cursor()
		c.execute("""
			SELECT MAX(last_scanned) as last_scanned FROM last_scanned;
		""")
		res = c.fetchone()
		print(res, res['last_scanned'])
		if res and res['last_scanned']:
			last_scanned = res['last_scanned']

			from_zone = tz.tzutc()
			to_zone = tz.tzlocal()

			last_scanned = datetime.datetime.strptime(last_scanned, '%Y-%m-%d %H:%M:%S')
			utc = last_scanned.replace(tzinfo=from_zone)
			local = utc.astimezone(to_zone)
			return local
		return datetime.datetime(2020,1,1,0,0)
		

	def update_last_scanned(self):
		c = self.conn.cursor()
		c.execute("""
			INSERT INTO last_scanned(last_scanned) VALUES(DATETIME('now'));
		""")
		self.conn.commit()

	def insert_into_message(self, message_id, create_date, guild_id):
		c = self.conn.cursor()
		c.execute("""
			INSERT INTO message(discord_id, guild_id, message_date)
			VALUES(?, ?, ?);
		""", (message_id, guild_id, create_date))
		#self.conn.commit()
		return c.lastrowid

	def insert_into_authors(self, author_id, author_name):
		c = self.conn.cursor()
		c.execute("""
			INSERT INTO user(user_id, username)
			VALUES(?, ?);
		""", (author_id, author_name))
		self.conn.commit()
		return c.lastrowid

	def insert_into_emote(self, emote_id, emote):
		# download the image
		img_data = requests.get(f"https://cdn.discordapp.com/emojis/{emote_id}.png").content
		b64 = base64.b64encode(img_data)
		encoded = str(b64, "utf-8")
		c = self.conn.cursor()
		c.execute("""
			INSERT INTO emote(discord_id, emote, base64_encoded_image)
			VALUES(?, ?, ?);
		""", (emote_id, emote, encoded))
		self.conn.commit()
		return c.lastrowid
	
	def find_emote(self, emote_id, emote):
		c = self.conn.cursor()
		c.execute("""
			SELECT rowid FROM emote WHERE discord_id = ? AND emote = ?;
		""", (emote_id, emote))
		return c.fetchone()['rowid']

	def get_emote_id(self, emote_id, emote):
		if (emote_id, emote) not in self.emotes:
			try:
				self.emotes[(emote_id, emote)] = self.insert_into_emote(emote_id, emote)
			except:
				self.emotes[(emote_id, emote)] = self.find_emote(emote_id, emote)
		return self.emotes[(emote_id, emote)]
	
	def get_author(self, author_id, author_name):
		if author_id not in self.authors:
			self.insert_into_authors(author_id, author_name)
			self.authors.add(author_id)

	def load_authors(self):
		c = self.conn.cursor()
		c.execute("""
			SELECT * FROM user;
		""")
		for row in c:
			self.authors.add(row['user_id'])

	def load_emotes(self):
		c = self.conn.cursor()
		c.execute("""
			SELECT rowid, * FROM emote;
		""")
		for row in c:
			self.emotes[(row['discord_id'], row['emote'])] = row['rowid']
		print('Loaded emotes', self.emotes)
		
	def insert_into_usage(self, message_id, emote_id, emote, num, author_id, author_name):
		self.get_author(author_id, author_name)
		emote_row_id = self.get_emote_id(emote_id, emote)

		c = self.conn.cursor()
		c.execute("""
			INSERT INTO usage(discord_id, emote_id, num)
			VALUES(?, ?, ?);
		""", (message_id, emote_row_id, num))
		#self.conn.commit()

	def insert_into_react(self, message_id, author_id, author_name, emote_id, emote):
		self.get_author(author_id, author_name)
		emote_row_id = self.get_emote_id(emote_id, emote)

		c = self.conn.cursor()
		c.execute("""
			INSERT INTO react(discord_id, emote_id, user_id)
			VALUES(?, ?, ?);
		""", (message_id, emote_row_id, author_id))
		#self.conn.commit()


	async def handle_message(self, message, guild):
		print('handling message', message.id, message.created_at)
		# find emotes inside the message
		emotes = []
		for group in EMOJI_REGEX_COMPILED.finditer(message.content):
			emotes.append(Emote(group.group('name'), group.group('id'), group.group('animated')))
		count = Counter(emotes)
		print('emotes', count)
		self.insert_into_message(message.id, message.created_at, guild.id)
		for emote, num in count.items():
			print('found emote usage', message.author, emote, num)
			print()
			self.insert_into_usage(message.id, emote.id, emote.name, num, message.author.id, message.author.name)
		# find reactions
		for reaction in message.reactions:
			print('found reactions', reaction)
			emoji_id = None
			emoji_name = None
			if type(reaction.emoji) != type('a'):
				emoji_id = reaction.emoji.id
				emoji_name = reaction.emoji.name
			else:
				emoji_name = reaction.emoji
			async for user in reaction.users():
				print('inserting reaction for user', user.name, emoji_name)
				self.insert_into_react(message.id, user.id, user.name, emoji_id, emoji_name)

	async def on_ready(self):
		print(f'Logged on as {self.user}!')

		last_scanned = self.get_last_scanned()
		print('Finding messages after', last_scanned)

		self.load_authors()
		self.load_emotes()

		for guild in client.guilds:
			if guild.id != 1083238120645992458: continue
			print('Connected to', guild)
			active_emojis = []
			# insert into emotes
			for emoji in guild.emojis:
				rowid = self.get_emote_id(emoji.id, emoji.name)
				if emoji.available:
					active_emojis.append((emoji, rowid))
			# update list of active emotes
			c = self.conn.cursor()
			c.execute("drop table if exists guild_emotes;")
			# emote id is the ROW ID not the discord id
			c.execute("create table guild_emotes (guild_id unsigned big int, emote_id unsigned);")
			for emoji, rowid in active_emojis:
				print('inserting active emote', emoji, rowid)
				c.execute("insert into guild_emotes(guild_id, emote_id) values (?, ?);", (guild.id, rowid))
			self.conn.commit()
			print('Finished inserting active emotes')
			
			for channel in guild.text_channels:				
				print('Reading channel', channel)
				try:
					async for message in channel.history(limit=None, after=last_scanned):
						c = self.conn.cursor()
						res = c.execute("""SELECT * FROM message WHERE discord_id = ?;""", (message.id,))
						if res.fetchone() is not None:
							print('Already seen message', message.created_at)
							continue

						await self.handle_message(message, guild)
				except:
					pass
				self.conn.commit()

		print('Done!')
		self.update_last_scanned()
		print('Updated last scan date. You can exit now!')
		await self.close()

	
if __name__ == "__main__":
	#asyncio.run(run_thing())
	intents = discord.Intents.default()
	intents.message_content = True
	conn = None
	try:
		conn = sqlite3.connect(DB_FILE)
		# for access by col names!
		conn.row_factory = sqlite3.Row
		client = MyClient(conn, intents=intents)
		client.run(TOKEN)
	except:
		pass
	finally:
		if conn:
			conn.close()


