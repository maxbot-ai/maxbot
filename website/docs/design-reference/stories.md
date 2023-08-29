# Stories engine

You can use the stories mechanism to test the bot.
This is a mechanism that verifies that the bot will react in the expected way to events known in advance from the user.
Events are grouped into separate stories, which are all described together in file as a list.
Multiple stories files can be grouped in a directory.

## `StorySchema`

Each story is an object and has the following set of fields:

| Name      | Type                                     | Description                                                       |
| --------- | ---------------------------------------- | ----------------------------------------------------------------- |
| `name`\*  | [String](/design-reference/strings.md)   | Printable name.                                                   |
| `turns`\* | List of [TurnSchema](#turnschema)        | List of story turns.                                              |
| `markers` | List of [Strings](/design-reference/strings.md) | List of [pytest marks](https://docs.pytest.org/en/stable/how-to/mark.html) |

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
(e.g. chosen by the bot's script using [`random`](/design-reference/lists/#filter-random))
then the `response` field should contain a list of strings.
One list item for each possible bot response.

```yaml
- name: seasons-random
  turns:
    - message: season
      response:
        - "Spring"
        - "Summer"
        - "Autumn"
        - "Winter"
```
