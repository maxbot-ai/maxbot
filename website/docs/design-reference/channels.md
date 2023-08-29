# Builtin channels

This document contains the description and settings configuration of MaxBot builtin channels.
You can expand your bot by [implementing a new channel](/coding-guides/channels.md)!

## Telegram

[Telegram Messenger](https://telegram.org/) is instant messaging service.
To make your bot available in this messenger you need to add channel `telegram` to the `channels` section.
The channel has the following configuration settings:

| Name          | Type | Description | See also |
| ------------- | ---- | ----------- | -------- |
| `api_token`\* | [String](/design-reference/strings.md) | Authentication token to access telegram bot api | https://core.telegram.org/bots#how-do-i-create-a-bot |
| `timeout`     | [Timeout](/design-reference/timeout.md) | Default HTTP request timeouts | https://www.python-httpx.org/advanced/#timeout-configuration |
| `limits`      | [Pool limits](/design-reference/pool-limits.md) | Pool limit configuration | https://www.python-httpx.org/advanced/#pool-limit-configuration |

## Facebook

[Facebook Messenger](https://www.messenger.com/) instant messaging application and platform developed by [Meta Platforms](https://meta.com/).
To make your bot available in this messenger you need to add channel `facebook` to the `channels` section.
The channel has the following configuration settings:

| Name             | Type | Description | See also |
| ---------------- | ---- | ----------- | -------- |
| `app_secret`\*   | [String](/design-reference/strings.md) | Facebook `App Secret` | https://developers.facebook.com/docs/facebook-login/security/#appsecret |
| `access_token`\* | [String](/design-reference/strings.md) | Facebook `App Access Tokens` | https://developers.facebook.com/docs/facebook-login/security/#appsecret |
| `timeout`     | [Timeout](/design-reference/timeout.md) | Default HTTP request timeouts | https://www.python-httpx.org/advanced/#timeout-configuration |
| `limits`      | [Pool limits](/design-reference/pool-limits.md) | Pool limit configuration | https://www.python-httpx.org/advanced/#pool-limit-configuration |

## Viber

[Rakuten Viber](http://viber.com/) is instant messaging software application.
To make your bot available in this messenger you need to add channel `viber` to the `channels` section.
The channel has the following configuration settings:

| Name          | Type | Description | See also |
| ------------- | ---- | ----------- | -------- |
| `api_token`\* | [String](/design-reference/strings.md) | Authentication token to access viber bot api | https://developers.viber.com/docs/api/rest-bot-api/#authentication-token |
| `name`        | [String](/design-reference/strings.md) | Bot name | https://developers.viber.com/docs/api/python-bot-api/#firstly-lets-import-and-configure-our-bot https://developers.viber.com/docs/api/python-bot-api/#userprofile-object |
| `avatar`      | [String](/design-reference/strings.md) | Bot avatar | https://developers.viber.com/docs/api/python-bot-api/#firstly-lets-import-and-configure-our-bot https://developers.viber.com/docs/api/python-bot-api/#userprofile-object |
| `timeout`     | [Timeout](/design-reference/timeout.md) | Default HTTP request timeouts | https://www.python-httpx.org/advanced/#timeout-configuration |
| `limits`      | [Pool limits](/design-reference/pool-limits.md) | Pool limit configuration | https://www.python-httpx.org/advanced/#pool-limit-configuration |

## VK

[VK](http://vk.com/) is online social media and social networking service.
To make your bot available in this messenger you need to add channel `vk` to the `channels` section.
The channel has the following configuration settings:

| Name             | Type | Description | See also |
| ---------------- | ---- | ----------- | -------- |
| `access_token`\* | [String](/design-reference/strings.md) | Authentication token to access VK bot api | https://dev.vk.com/api/access-token/authcode-flow-user |
| `group_id`       | [Integer](/design-reference/numbers.md) | `group_id` for VK page, if present, the incoming messages will be checked against it and use for set webhook | |
| `secret_key`     | [String](/design-reference/strings.md) | Secret key, use for set webhook | https://dev.vk.com/method/groups.addCallbackServer |
| `server_title`   | [String](/design-reference/strings.md) | Server title, use for set webhook | https://dev.vk.com/method/groups.addCallbackServer |
| `timeout`        | [Timeout](/design-reference/timeout.md) | Default HTTP request timeouts | https://www.python-httpx.org/advanced/#timeout-configuration |
| `limits`         | [Pool limits](/design-reference/pool-limits.md) | Pool limit configuration | https://www.python-httpx.org/advanced/#pool-limit-configuration |
