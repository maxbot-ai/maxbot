---
title: MaxBot Command Line Interface
sidebar_label: MaxBot CLI
---
# MaxBot Command Line Interface (CLI)

Maxbot’s CLI provides a range of helpful commands for run the bot and run bots stories.
For a list of available commands, you can type maxbot --help.
You can also add the --help flag to any command or subcommand to see the description, available arguments and usage.

## info

Print information about your Maxbot installation.

```bash
$ maxbot info

Maxbot version             0.2.0
Python version             3.9.16
Platform                   macOS-13.3-arm64-arm-64bit
Location                   /your/location

```

## run

Run the bot.

| Name                         | Description |
| ---------------------------- | ----------- |
| -B, --bot TEXT               | Path for bot file or directory or the Maxbot instance to load. The instance can be in the form 'module:name'. Module can be a dotted import. Name is not required if it is 'bot'. [required] |
| --updater [webhooks\|polling] | The way your bot geting updates from messaging platforms. The 'polling' updater is only available for telegram channel. By default, the most appropriate value is selected.|
| --host TEXT                  | Hostname or IP address on which to listen. [default: localhost] |
| --port INTEGER               | TCP port on which to listen. [default: 8080] |
| --public-url TEXT            | A URL that is forwarded to http://&lthost&gt:&ltport&gt/. This is used to register webhooks to get updates for the channels. If missing, no webhooks are registered and you have to register them yourself.|
| --ngrok                      | Obtain host, port and public URL from ngrok. |
| --ngrok-url TEXT             | An URL to ngrok's web interface. [default: http://localhost:4040] |
| --reload / --no-reload       | Watch bot files and reload on changes. |
| -v, --verbose                | Set the verbosity level. |
| --logger TEXT                | Write the developer logs to console or file:/path/to/file.log. Use the --journal-file option to redirect the journal. [default: console]|
| -q, --quiet                  | Do not log to console. |
| --journal-file FILENAME      | Write the journal to the file |
| --journal-output [json\|yaml] | Journal file format [default: json] |
| --workers                    | Number of web application worker processes to spawn. |
| --fast                       | Set the number of web application workers to max allowed. |
| --single-process             | Run web application in a single process. |
| --help                       | Show this message and exit. |
