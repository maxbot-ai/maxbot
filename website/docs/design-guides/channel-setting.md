import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Channel setting

## Overview

The latest version of `Maxbot` has a built-in support of `Telegram`, `Viber` and `VK` messengers, but you can always [add the messenger you need](/coding-guides/channels).
Each messenger has its own differences in controls, features, etc. If you want to expand the possibilities of dialogue, for example, add sending location to `Viber` or sending money to `VK`, read about it in [Coding Guide](/category/coding-guides).

## Telegram

If a bot in `Telegram` messenger has already created, the steps 1 - 5 described below can be skipped.
To set up bot integration with `Telegram` it is necessary:
1. Open the `Telegram` messenger.
2. Go [@BotFacther](https://t.me/botfather) and send `/start` command to the dialog.
3. Send the `/newbot` command.
4. Set the user and system name for the new bot.
5. Save the resulting bot token.
6. Specify parameter in the bot resources. You can find all of them in [Telegram schema](/design-reference/channels/#telegram):

```yaml
channels:
  telegram:
    api_token: 110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
```

## Viber

Connection to `Viber` is similar to connection to `Telegram`. You need to create a bot and get an API token, see [instruction](https://developers.viber.com/docs/api/rest-bot-api/#get-started).

If the company has already created a bot in Viber, the steps 1 - 4 described below can be skipped.
To set up bot integration with `Viber` you need to:
1. Go to [link](https://partners.viber.com/login) and enter the control panel.
2. Click on `Create Bot Account`.
3. Fill in the data for the bot and click on `Create`.
4. The account will be created. The next window will display the token that you need to use in `Maxbot` to integrate the bot with `Viber` messenger.
5. Specify parameter in the bot resources. You can find all of them in [Viber schema](/design-reference/channels/#viber):

```yaml
channels:
  viber:
    api_token: 511c56j76j44dcb2-d80de780c65cd798-cbdf5833d0a9aa3c
```

## VK

If the company has already had a `VK` community to integrate with the bot, the steps 1 - 5 described below can be skipped. Steps 6 to 11 are mandatory.
To configure the integration of the bot with the `VK` community it is necessary:
1.  Log in to the `VK` social network.
2.  Go to the section `Communities`.
3.  In the section `Communities` click on the button `Create community`.
4.  In the opened window fill in the name and theme of the community.
5.  Click on `Create community`.
6.  On the community page click on the link `Manage`.
7.  In the list of sections of settings click on `API usage`-> `Callback API` -> `Secret key`.
8.  Fill in the `Secret key` field by yourself. This is a `secret_key` parameter.
9.  Select a tab `Access tokens` -> `Show`. This is a `access_token` parameter.
10. Look at the URL of your community. The numbers in the string is the `group_id` parameter.
11. Specify parameters in the bot resources. You can find all of them in [VK schema](/design-reference/channels/#vk):

```yaml
channels:
  vk:
    secret_key: 9rLP4x4xLX4fg
    access_token: 99fa2e47fe664da97f3d166c7c32c226370ef9d6e5026a97f3d166c7c32c226370026160db99
    group_id: 123456789
```