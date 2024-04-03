# emoji-counter
* Requires you to install docker
* Be inside the directory when you run it (it uses $PWD)
* Run ./start.sh to start
* Run ./stop.sh to stop
* You can see the docker compose has a bunch of volumes. you'll
    need to change the paths to match your own.
* Also inside the root folder you need a `.env` file with
```
DB_FILE=/path/to/your/db.sqlite
TOKEN=your-discord-bot-token
```
