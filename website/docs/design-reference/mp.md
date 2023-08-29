# Multiprocess WEB application

To receive incoming messages, the bot can work in two modes: `webhooks` and `polling` (see [run --updater argument](/design-reference/cli.md#run)).
The current document only describes operation in `webhooks` mode.
Mode `webhooks` implies that the bot acts as an HTTP server.
The server receives and processes incoming HTTP requests.
Such server is called WEB application.

The bot handles incoming requests with concurrent code (asynchronous I/O).
If your bot can't handle the incoming load you can scale incoming requests processing to multiple processes.
You can control the number of processes handling incoming requests with command line argument [--workers](/design-reference/cli.md#run).
Or you can specify [--fast](/design-reference/cli.md#run) option to automatically determine the number of processes for best performance.

Working in multi-process mode has its own characteristics and imposes a number of requirements.
If your bot code is not designed to work in several processes, you can force it to work in single process mode with [--single-process option](/design-reference/cli.md#run).

## Workers

The processes responsible for handling incoming HTTP requests are called workers.
The bot implements a user locking mechanism,
so all incoming user messages are processed sequentially for each user (including sending reply commands).
Messages from different users can be processed simultaneously both in one worker (concurrent code, asynchronous I/O)
and in different workers (processes).
You can implement your own custom user lock that will meet the same requirements.

## Persistence storage

By default, we use SQLite as our storage engine.
It allows multiple processes to work on a single database file.
But this engine does not allow parallel writes.
This can cause serious performance issues.
Therefore, we recommend using a different database engine (such as PostgreSQL, MySQL) for highly loaded solutions.
For details, see [SQLite FAQ](https://www.sqlite.org/faq.html#q5).

A unique persistent storage file in a temporary directory is generated for each bot run.
It is not deleted when the bot is stopped.
You can delete the storage files yourself after stopping the bot.
For example (unix-like systems): files can be deleted with `rm /tmp/maxbot-*.db` command.

## Known issues

MaxBot uses [sanic](https://sanic.dev/en/) as a web application framework.
Unfortunately, there are unresolved issues in `sanic` that lead to various random exceptions when trying to shut down the bot by pressing Ctrl-C.
Examples of such exceptions can be found [here](https://community.sanicframework.org/t/random-exceptions-with-workermanager/1154).

