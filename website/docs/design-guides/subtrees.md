# Subtrees

You can group dialog nodes together by creating a subtree. There are lots of reasons to group nodes.

* To store a large dialog tree in multiple files. As the number of nodes increases, the dialog tree becomes difficult to maintain. It is more convenient to split the tree into several subtrees and store each subtree in a separate file.
* To keep nodes that address a similar subject together to make them easier to find. For example, you might group nodes that address questions about user accounts in a User account subtree and nodes that handle payment-related queries in a Payment subtree.
* To group together a set of nodes that you want the dialog to process only if a certain guard condition is met. Use a guard condition, such as `user.is_platinum_member`, for example, to group together nodes that offer extra services that should only be processed if the current user is entitled to receive the extra services.
* To hide nodes from the runtime while you work on them. You can add the nodes to a subtree with a `false` guard condition to prevent them from being processed.

## Create a subtree

You may want to make certain nodes available only to registered users. You can add an additional check `user.is_registered` to the conditions of these nodes.

```yaml
dialog:
  - condition: intents.greetings
    response: |
        Good day to you!
#highlight-start
  - condition: intents.order_inform and user.is_registered
#highlight-end
    response: |
        Here is a list of your orders...
#highlight-start
  - condition: intents.show_profile and user.is_registered
#highlight-end
    response: |
        Here is your profile...
  - condition: intents.about_you
    response: |
        My name is MaxBot.
```

You can do it the other way, put all such nodes into a subtree and move the `user.is_registered` check from node's conditions to the guard condition of the subtree.

You create a subtree in a separate file in the `dialog/` subdirectory of the bot's [resource directory](/getting-started/creating-bots.md#resource-directory). It is recommended to name the file according to the name of the subtree. So create a file `dialog/registered-users.yaml` and put the following content in it:

```yaml
name: registered_users
guard: user.is_registered
nodes:
  - condition: intents.order_inform
    response: |
        Here is a list of your orders...
  - condition: intents.show_profile
    response: |
        Here is your profile...
```

Then you include your subtree in the dialog tree in `bot.yaml` like this:

```yaml
dialog:
  - condition: intents.greetings
    response: |
        Good day to you!
#highlight-start
  - subtree: registered_members
#highlight-end
  - condition: intents.about_you
    response: |
        My name is MaxBot.
```

In the example you include a subtree at the root level of the tree. You can also include subtree at the child level. All context variables are available in subtree nodes.

:::caution

You can include a subtree into a tree only once. Node labels must remain unique throughout the entire dialog tree, including subtrees.

:::

See [Jinja Loader](/extensions/jinja_loader) guide if you want to reuse your templates in multiple responses.

## Subtree Processing

These characteristics of the subtree impact how the nodes in a subtree are processed.

* **Guard condition.** If no guard condition is specified, then your bot processes the nodes within the subtree directly. If a guard condition is specified, your bot first evaluates the condition to determine whether to process the nodes within the subtree.

* **Tree hierarchy**. Nodes in a subtree are treated as root or followup nodes based on whether the subtree is added to the dialog tree at the root or child level. Any root level nodes that you add to a root level subtree continue to function as root nodes; they do not become followup nodes of the subtree, for example. However, if you move a root level node into a subtree that is a child of another node, then the root node becomes a followup node of that other node.

Subtrees have no impact on the order in which nodes are evaluated. Nodes continue to be processed from first to last. As your bot travels down the tree, when it encounters a subtree, if the subtree has no guard condition or its condition is true, it immediately processes the first node in the subtree, and continues down the tree in order from there. If a subtree does not have a guard condition, then the subtree is transparent to your bot, and each node in the subtree is treated like any other individual node in the tree.

You can use the `jump_to` command to jump between any nodes in the dialog, whether those nodes are in subtrees or not.

:::caution

When your `jump_to` command targets a node in a subtree, that subtree's **guard condition is not checked**. Moreover, if your `jump_to` command [targets a condition](/design-guides/dialog-tree.md#jump_to) of a node in a subtree, the bot **only processes siblings nodes whithin that subtree**.

:::
