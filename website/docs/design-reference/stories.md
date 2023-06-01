# Stories engine

You can use the stories mechanism to test the bot.
This is a mechanism that verifies that the bot will react in the expected way to events known in advance from the user.
Events are grouped into separate stories, which are all described together in one file as a list.

## `StorySchema`

Each story is an object and has the following set of fields:

| Name      | Type                                     | Description                                                       |
| --------- | ---------------------------------------- | ----------------------------------------------------------------- |
| `xfail`   | [Boolean](/design-reference/booleans.md) | The flag means that you expect the story to fail for some reason. |
| `name`\*  | [String](/design-reference/strings.md)   | Printable name.                                                   |
| `turns`\* | List of [TurnSchema](#turnschema)        | List of story turns.                                              |

## `TurnSchema`

One step of history. It is an object and has the following set of fields:

| Name         | Type                                                         | Description                                                |
| ------------ | ------------------------------------------------------------ | ---------------------------------------------------------- |
| `utc_time`   | [String](/design-reference/strings.md)                       | Date and time string of the story step in ISO 8601 format. |
| `message`    | [MessageSchema](/design-reference/protocol.md#messageschema) | Incoming message from customer.                            |
| `rpc`        | RpcRequestSchema                                             | Incoming RPC event.                                        |
| `response`\* | [String](/design-reference/strings.md)                       | Expected bot response.                                     |

One of the fields **must be filled** in the `TurnSchema` object: `message` or `rpc`.

If no time zone is specified in the `TurnSchema.utc_time` field, then the value will be considered in UTC.
If the `TurnSchema.utc_time` field contains a value with any time zone other than UTC, then the value will be converted to the UTC time zone.

After a step with the `TurnSchema.utc_time` field explicitly specified, all subsequent steps without this field will be shifted forward by 10 seconds.

If the bot can respond with one of the predefined answers
(e.g. chosen by the bot's script using `random`)
then the `response` field should contain a list of strings.
One list item for each possible bot response.
