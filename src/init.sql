CREATE TABLE if not exists message(
	discord_id UNSIGNED BIG INT,
	guild_id UNSIGNED BIG INT,
	message_date timestamp
);
create index if not exists discordId on message(discord_id);
create index if not exists guildId on message(guild_id);


CREATE TABLE if not exists emote(
	discord_id UNSIGNED BIG INT,
	emote text,
    base64_encoded_image text,
    unique(discord_id, emote)
);
create index if not exists emoteId on emote(discord_id);

-- note: emote_id is the ROW id, not the emote id!
create table if not exists react(
	discord_id UNSIGNED BIG INT,
	emote_id integer,
	user_id integer,
	unique(discord_id, emote_id, user_id)
);
create index if not exists reactId on react(discord_id);

create table if not exists user(
	user_id UNSIGNED BIG INT primary key,
	username text
);
create index if not exists userId on user(user_id);

-- this is ROW id too
create table if not exists usage(
	discord_id UNSIGNED BIG INT,
	emote_id integer,
	num integer
);
create index if not exists usageId on usage(discord_id);


create table if not exists last_scanned(
	last_scanned timestamp
);