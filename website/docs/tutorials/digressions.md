---
toc_min_heading_level: 2
toc_max_heading_level: 2
---

# Understanding Digressions

In this tutorial, you see firsthand how digressions work.

By the time you finish the tutorial, you will understand how:

* digressions are designed to work,
* to control digression flow,
* to test digression settings for a dialog.

The source code of the bot is available on github: [digression-showcase](https://github.com/maxbot-ai/maxbot/tree/main/examples/digression-showcase).

## Prerequisite

Before you begin, complete the [Quick Start](/getting-started/quick-start.md) tutorial.

Create a `bot.yaml` file and put [source code](https://github.com/maxbot-ai/maxbot/tree/main/examples/digression-showcase/bot.yaml) of the example into the file.

Change channel settings, for example, we use telegram channel:

```yaml
channels:
  telegram:
    api_token: 110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
```

## Temporarily digressing away from node

Digressions allow users to break away from a dialog branch to temporarily change the topic before they return to the original dialog flow. In this step, you will start to book a restaurant reservation, then digress away to ask for the restaurant's hours. After providing the opening hours information, your assistant will return back to the restaurant booking dialog flow.

Run the bot.

```bash
$ maxbot run --bot bot.yaml
✓ Started polling updater... Press 'Ctrl-C' to exit.
```

Open your messenger and try to make a reservation.

* Type `Book me a restaurant`. The bot responds with a prompt for the day to reserve, *When do you want to go?*
* Type `Tomorrow`. The bot responds with a prompt for the time to reserve, *What time do you want to go?*
* You do not know when the restaurant closes, so you ask, `What time do you close?` The bot digresses away from the  restaurant booking node to process the **restaurant opening hours** node. It responds with, *The restaurant is open from 8:00 AM to 10:00 PM.* The bot then returns to the restaurant booking node, and prompts you again for the reservation time.
* Optional: To complete the dialog flow, type `at 8pm` for the reservation time and `2` for the number of guests.

Congratulations! You successfully digressed away from and returned to a dialog flow.

:::tip
You digressed away from a node with slots. Similarly you can digress away from parent node which contains followup nodes. You can try it youself. Just type  `Do you have any job openings?` to trigger the `job_opportunities` node and then try to change the topic.
:::

## Digressing from a node that is configured not to return to it

In this step, you will use the digression setting for the parent node to prevent users from returning after digressing away from it, and see how the setting change impacts the dialog flow.

In previous section, you saw that after you digressed away from the restaurant booking node to go to the restaurant opening hours node, your assistant went back to the restaurant booking node to continue with the reservation process. In this section, you will digress away from the `job_opportunities_for_chef` node to ask about restaurant opening hours and see that your assistant does not return to where it left off. This happens because the `job_opportunities_for_chef` node has a `after_digression_followup` setting set to `never_return`.

Let's look at the digression settings for the `job_opportunities_for_chef` node.

```yaml
- condition: entities.job_role.chef
  label: job_opportunities_for_chef
  response: |
    We have a fabulous cooking staff.
    How many years of experience do you have?
# highlight-start
  settings:
      after_digression_followup: never_return
# highlight-end
  followup:
    # ...
```

Now, run the bot and open your messenger.

* Type `I'm interested in a job` The bot responds by saying, *What kind of work are you interested in?*
* Type `chef`. The bot triggers `job_opportunities_for_chef` node asks you about your experience: *We have a fabulous cooking staff. How many years of experience do you have?*
* Change the topic by typing, `What time do you close?`. The bot digresses away from the `job_opportunities_for_chef` node to process the restaurant opening hours node. It responds with, *The restaurant is open from 8am to 8pm.* The bot then does not return to the `job_opportunities_for_chef` node. So, if you still need a job, you should start the `job_opportunities` topic again.

You successfully prevented the bot from returning to a node after you digressing away from it.

## Digressing to a node that prevent returns

You can use `end` control command to prevent a dialog node from returning to the node that your bot digressed away from for the current node to be processed.

To demonstrate this configuration, you will change the digression setting for the restaurant hours node. In Step 2, you saw that after you digressed away from the restaurant booking node to go to the restaurant opening hours node, your assistant went back to the restaurant booking node to continue with the reservation process.

In this section, you will digress away from the restaurant booking dialog to ask bot to cancel the process and see that your assistant does not return to where it left off.

The `intents.cancel` node uses the `end` control command to prevent returns.

```yaml
  - condition: intents.cancel
    response: |
      Ok, cancelling the task.
      <end />
```

* To engage the restaurant booking dialog node, type, `Book me a restaurant`. The bot responds with a prompt for the day to reserve, *When do you want to go?*
* Instead of answering this question, ask the bot to exit a process. Type `I do not want to do this`. The bot digresses away from the restaurant booking node to the `intents.cancel` node to answer your question. Your assistant responds with *Ok, cancelling the task*.

Unlike in the test above, this time the dialog does not pick up where it left off in the restaurant booking node. The bot does not return to the dialog that was in progress because you use the `end` command to not return.

## Conclusion

In this tutorial you experienced how [digressions](/design-guides/digressions) work, and saw how you can impact the digressions behavior.
