# RPC

You can use MaxBot RPC to send messages by a bot that isn't in response to a request from a user. Examples of such proactive messages are notifications and scehduled messages.

You define the RPC methods and their parameters (required and optional) in the bot file.

```yaml
rpc:
  - method: order_shipped
    params:
      - name: order_id
        required: true
      - name: delivered_days
```

Then you process RPC methods and their params in the dialog tree in the same way as that you process intents and entities.

```django
dialog:
  - condition: rpc.order_shipped
    response: |
      Your order #{{ params.order_id }} has been shipped.
      {% if params.delivered_days %}
          It will be delivered within the next {{ params.delivered_days }} days.
      {% endif %}
```

Given the `rpc` section in you bot file the maxbot will create HTTP endpoints that will be ready to process you RPC requests.

```bash
$ maxbot run --bot bot.yaml
⚠  Make sure you have a public URL that is forwarded to -> http://localhost:8080/telegram and register webhook for it.
✓ Started webhooks updater on http://localhost:8080. Press 'Ctrl-C' to exit.
```

Just call the desired RPC method when you want to send a proactive message to the user. The RPC endpoint URL should contain the name of the channel ("telegram") and the ID (associated with the channel) of the user to whom you want to send a message ("1234567890").

```bash
$ curl http://localhost:8080/rpc/telegram/1234567890 \
    -d '{"method": "order_shipped", "params": {"order_id": 123}}'
{"result":null}
```

The user will receive a proactive message. The MaxBot CLI output will look like this.

```yaml
[18:55:24], telegram#127942701
💡 method: order_shipped
   params:
     order_id: 123
🤖 Your order #123 has been shipped.
```