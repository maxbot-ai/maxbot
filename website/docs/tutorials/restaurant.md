---
toc_min_heading_level: 2
toc_max_heading_level: 2
---

# Restaurant Bot

In this tutorial, you create a bot that helps users with inquiries about a fictitious restaurant called Truck Stop Gourmand.

By the time you finish the tutorial, you will understand how to:

* Define intents.
* Add dialog nodes that can handle your intents.
* Use commands to send text and media responses.
* Add entities to make your responses more specific.
* Add a pattern entity, and use it in the dialog to find patterns in user input.
* Set and reference state variables

The source code of the bot is available on github: [restaurant](https://github.com/maxbot-ai/maxbot/tree/main/examples/restaurant).

### Prerequisite

Before you begin, complete the [Quick Start](/getting-started/quick-start.md) tutorial.

Create a `bot.yaml` file that will contain the source code of the bot.

Add channel settings, for example, we use telegam channel:

```yaml
channels:
  telegram:
    api_token: 110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
```

## Plan the dialog

You are building a bot for a restaurant named Truck Stop Gourmand that has one location and a thriving cake-baking business. You want the simple bot to answer user questions about the restaurant, its menu, and to cancel customer cake orders. Therefore, you need to create intents that handle inquiries related to the following subjects:

* Restaurant information.
* Menu details.
* Order cancellations.

You'll start by creating intents that represent these subjects, and then build a dialog that responds to user questions about them.

## Answer questions about the restaurant

### Add an intent

Add an intent `intents.about_restaurant` that recognizes when customers ask for details about the restaurant. Provide examples of utterances that real users might enter to trigger this intent.

```yaml
- name: about_restaurant
  examples:
    - Tell me about the restaurant
    - i want to know about you
    - who are the restaurant owners and what is their philosophy?
    - What's your story?
    - Where do you source your produce from?
    - Who is your head chef and what is the chef's background?
    - How many locations do you have?
    - do you cater or host functions on site?
    - Do you deliver?
    - Are you open for breakfast?
```

### Add a dialog node

Add a dialog node that recognizes when the user input maps to the intent that you created, meaning its condition checks whether your bot recognized the `intents.about_restaurant` intent from the user input.

```yaml
- condition: intents.about_restaurant
  response: |
      <image url="https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg"/>
      Truck Stop Gourmand is the brainchild of Gloria and Fred Smith.
      What started out as a food truck in 2004 has expanded into a
      thriving restaurant. We now have one brick-and-mortar restaurant
      in downtown Portland. The bigger kitchen brought with it new chefs,
      but each one is faithful to the philosophy that made the Smith food
      truck so popular to begin with deliver fresh, local produce in
      inventive and delicious ways.


      Join us for lunch or dinner seven days a week. Or order a cake from
      our bakery.

```

The response consists of two commands. The `image` command includes image in the response. An `url` argument contains the full URL to the hosted image.

The `text` command contains a long statement about the restaurant. The folded (`|`) string style allows you to break long line into multiple lines for easier editing. When sent to the user, these lines will be combined into one, so your messenger can wrap words itself. To get a newline leave a blank line by putting two newlines in.

### Run and test

Now you can run the bot

```bash
$ maxbot run --bot bot.yaml
✓ Started polling updater... Press 'Ctrl-C' to exit.
```

Open your messenger and ask your bot about the restaurant. For example, `Tell me about the restaurant`.

Your bot returns a response with the image and text that you specified for the dialog node. The output in your console will look like this

```yaml
🧑 Tell me about the restaurant
🤖 <image url="https://raw.githubusercontent.com/maxbot-ai/misc/main/food_1.jpg" />
   <text>
     Truck Stop Gourmand is the brainchild of Gloria and Fred Smith.
     What started out as a food truck in 2004 has expanded into a
     thriving restaurant. We now have one brick-and-mortar restaurant
     in downtown Portland. The bigger kitchen brought with it new chefs,
     but each one is faithful to the philosophy that made the Smith food
     truck so popular to begin with deliver fresh, local produce in
     inventive and delicious ways.
     Join us for lunch or dinner seven days a week. Or order a cake from
     our bakery.
   </text>
```

Check the answer in your messenger. You will see and image and a text. With the folded string style, text that you split into lines for convenience is now merged onto a single line, except for those lines that are separated by a blank line.

Congratulations! You have added an intent and a dialog node that knows how to handle it.

## Answer questions about the menu

A key question from potential restaurant customers is about the menu. The Truck Stop Gourmand restaurant changes the menu daily. In addition to its standard menu, it has vegetarian and cake shop menus. When a user asks about the menu, the dialog needs to find out which menu to share, and then provide a hyperlink to the menu that is kept up to date daily on the restaurant's website. More advanced implementation could get the menu through the restaurant website API and display it directly in the messenger.

### Add an intent

Add the following intent with examples:

```yaml
- name: menu
  examples:
    - I want to see a menu
    - What do you have for food?
    - Are there any specials today?
    - where can i find out about your cuisine?
    - What dishes do you have?
    - What are the choices for appetizers?
    - do you serve desserts?
    - What is the price range of your meals?
    - How much does a typical dish cost?
    - tell me the entree choices
    - Do you offer a prix fixe option?
```

### Add a dialog node

Add a dialog node that recognizes when the user input maps to the intent that you created, meaning its condition checks whether your assistant recognized the `intents.menu` intent from the user input.

In the bot's response we use `quick_reply` command that provides a text message and a list of options for the user to choose from. In this case, the list of options includes the different versions of the menu that are available.

TODO: until the quick\_reply command is implemented, we manage with a text message.

```yaml
- condition: intents.menu
  response: |
    In keeping with our commitment to giving you only fresh local ingredients,
    our menu changes daily to accommodate the produce we pick up in the morning.
    You can find today's menu on our website.

    Which menu do you want to see? [Standard] [Vegetarian] [Cake shop]
```

### Add phrase entity

To recognize the different types of menus that customers indicate they want to see, you will add a `entities.menu` entity. Entities represent a class of object or a data type that is relevant to a user's purpose. By checking for the presence of specific entities in the user input, you can add more responses, each one tailored to address a distinct user request. In this case, you will add an `entities.menu` entity that can distinguish among different menu types.

```yaml
entities:
  - name: menu
    values:
      - name: standard
        phrases:
        - standard
        - carte du jour
        - cuisine
      - name: vegetarian
        phrases:
        - vegetarian
        - vegan
        - plants-only
      - name: cake
        phrases:
        - cake shop
        - desserts
        - bakery offerings
```

The `entities.menu` entity contains values for three menu types: `standard`, `vegetarian`, `cake`. For each value, phrases are specified by which this value is recognized.

### Add followup nodes

In this step, you will add followup nodes to the dialog node that checks for the `intents.menu` intent. Each followup node will show a different response depending on the `entities.menu` entity type the user chooses from the options list.

You will add a followup node to handle each menu type option that you added to the `intents.menu` node.

```yaml
  - condition: intents.menu
    label: menu
    response: |
          {# ... #}
    followup:
      - condition: entities.menu.standard
        response: |
            To see our menu, go to the https://www.example.com/menu.html.
      - condition: entities.menu.vegetarian
        response: |
            To see our vegetarian menu, go to the https://www.example.com/vegetarian-menu.html.
      - condition: entities.menu.cake
        response: |
            To see our cake shop menu, go to the https://www.example.com/cake-menu.html.
```

The parent node has one more field - `label: menu`. A unique label is required for all nodes with followup and slot\_filling blocks. Such nodes add a new state to the dialog. The state must be distinguished from others and stored persistently. This requires a unique label.

The standard menu is likely to be requested most often, so you may want to move it to the end of the followup nodes list. Placing it last can help prevent it from being triggered accidentally when someone asks for a specialty menu instead the standard menu. For example, the message `"I am interested in vegetarian[menu:vegetarian] cuisine[menu:standard]"` will recognize two entity values. In this case, the bot's response will depend on the order of the nodes.

You have added nodes that recognize user requests for menu details. Your response informs the user that there are three types of menus available, and asks them to choose one. When the user chooses a menu type, a response is displayed that provides a hypertext link to a web page with the requested menu details.

### Run and test

Test the dialog nodes that you added to recognize menu questions.

Run the bot.

```bash
$ maxbot run --bot bot.yaml
✓ Started polling updater... Press 'Ctrl-C' to exit.
```

Open your messenger and enter, "What do you have for food?". The bot recognizes the `intents.menu` intent and displays the list of menu options for the user to choose from. In the console you will see

```
🧑 What do you have for food?
🤖 In keeping with our commitment to giving you only fresh local ingredients, our menu changes daily to accommodate the produce we pick up in the morning. You can find today's menu on our website.
   Which menu do you want to see? [Standard] [Vegetarian] [Cake shop]
```

Click the "Cake shop" option. Your bot recognizes the `entities.menu.cake` entity value, and displays the response

```
🧑 Cake shop
🤖 To see our cake shop menu, go to the https://www.example.com/cake-menu.html.
```

Well done. You have succesfully added an intent and entity that can recognize user requests for menu details, and can direct users to the appropriate menu.

## Manage cake orders

Customers place orders in person, over the phone, or by using the order form on the website. After the order is placed, users can cancel the order through the bot. First, define an entity that can recognize order numbers. Then, add an intent that recognizes when users want to cancel a cake order.

### Add regex entity

You want the bot to recognize order numbers, so you will create a regex entity to recognize the unique format that the restaurant uses to identify its orders. The syntax of order numbers used by the restaurant's bakery is 2 uppercase letters followed by 5 numbers. For example, YR34663. Add an entity that can recognize this character pattern.

```yaml
entities:
  - name: order_number
    values:
      - name: order_syntax
        regexps:
          - '[A-Z]{2}\d{5}'
```

### Add a cancel order intent

Add an intent that recognizes when the user wants to cancel the order.

```yaml
- name: cancel_order
  examples:
    - I want to cancel my cake order
    - I need to cancel an order I just placed
    - Can I cancel my cake order?
    - I'd like to cancel my order
    - There's been a change. I need to cancel my bakery order.
    - please cancel the birthday cake order I placed last week
    - The party theme changed; we don't need a cake anymore
    - that order i placed, i need to cancel it.
```

### Add a yes intent

Before you perform an action on the user's behalf, you must get confirmation that you are taking the proper action. Add a `intents.yes` intent to the dialog that can recognize when a user agrees with what your bot is proposing.

```yaml
- name: "yes"
  examples:
    - "Yes"
    - Correct
    - Please do.
    - You've got it right.
    - Please do that.
    - that is correct.
    - That's right
    - yeah
    - Yup
    - Yes, I'd like to go ahead with that.
```

### Handle requests to cancel a cake order

Add a dialog node that can handle requests to cancel a cake order.

```yaml
- condition: intents.cancel_order
  label: cancel_order
  response: |
    If the pickup time is more than 48 hours from now, you can cancel your order.
```

Before you can actually cancel the order, you need to know the order number. The user might specify the order number in the original request. So, to avoid asking for the order number again, check for a number with the order number pattern in the original input.

Now, add followup nodes that either ask for the order number or get confirmation from the user that she wants to cancel an order with the detected order number.

### Ask for an order number

Add a followup node to ask the user for the order number.

```yaml
- condition: intents.cancel_order
  label: cancel_order
# highlight-start
  response: |
    If the pickup time is more than 48 hours from now, you can cancel your order.
    <followup />
  followup:
    - condition: true
      label: ask_order_number
      response: |
        What is the order number?
# highlight-end
```

The parent node's response is now modified to use two commands. The `text` command displays the response, and the `followup` command instructs the bot to skip waiting for user input and immediately evaluate followup nodes. An expression `true` in the followup node's condition means that the order number must always be asked for now.

Now go deeper. Add a couple of followup nodes to the `ask_order_number` node. This nodes will process the user's response to the question about the order number:

* a node that informs the user that you are canceling the order;
* another node to capture the case where a user provides a number, but it is not a valid order number.

```yaml
- condition: intents.cancel_order
  label: cancel_order
  response: |
    If the pickup time is more than 48 hours from now, you can cancel your order.
    <followup />
  followup:
    - condition: true
      label: ask_order_number
      response: |
        What is the order number?
# highlight-start
      followup:
        - condition: entities.order_number
          response: |
              {% set order_number = entities.order_number.literal %}
              OK. The order {{ order_number }} is canceled.
              We hope we get the opportunity to bake a cake for you sometime soon.
        - condition: true
          response: |
              I need the order number to cancel the order for you. <br />
              If you don't know the order number, please call us
              at 958-234-3456 to cancel over the phone.
# highlight-end
```

A node with the `entities.order_number` condition is triggererd when the user provides correct order number. This node uses template to substitute order number into the response.

Local variables are used to store intermediate values inside templates. The order number is stored in the local variable `order_number` using the [local assignment](/design-reference/jinja#local-assignment):

```django
{% set order_number = entities.order_number.literal %}
```

The `entities.order_number.literal` expression results in a part of the user input containing the order number. The variable is then substituted in the response to the user.

```django
OK. The order {{ order_number }} is canceled.
```

The second followup node is triggered in all other cases where the user input is not relevant to the question. In this case, we explain to the user what went wrong and offer to cancel the order by phone.

### Get confirmation from the user

Add a followup node to the `cancel_order` node that responds in the case where the user provides the order number in the initial request, so you don't have to ask for it again.

```yaml
  - condition: intents.cancel_order
    label: cancel_order
    response: |
      If the pickup time is more than 48 hours from now, you can cancel your order.
      <followup />
    followup:
# highlight-start
      - condition: entities.order_number
        label: order_number_provided
        response: |
            {% set slots.order_number = entities.order_number.literal %}
            Just to confirm, you want to cancel order {{ slots.order_number }}?
# highlight-end
      - condition: true
        label: ask_order_number
        response: What is the order number?
        followup:
            # ...
```

Note that the `order_number_provided` node is listed first in the list of followup nodes, as its condition is more specific.

In the node's response, we define a slot variable `slots.order_number` that stores the order number using the [slot assignment](/design-reference/jinja#slot-assignment):

```django
{% set slots.order_number = entities.order_number.literal %}
```

We use a slot variable instead of a local variable because we need its value  not only in the current template, but also in followup nodes below.

You must add followup nodes that check for the user's response to your confirmation question.

```yaml
- condition: entities.order_number
  label: order_number_provided
  response: |
      {% set slot.order_number = entities.order_number.literal %}
      Just to confirm, you want to cancel order {{ slots.order_number }}?
# highlight-start
  followup:
    - condition: intents.yes
      response: |
          OK. The order {{ slots.order_number }} is canceled.
          We hope we get the opportunity to bake a cake for you sometime soon.
    - condition: true
      response: |
        <jump_to node="ask_order_number" transition="condition" />
# highlight-end
```

The `intents.yes` node uses the slot variable we defined in the parent node to respond to the user. The "anything else" node does not send any response, instead it uses the `jump_to` command to redirect users to a branch that requests the order number details you created earlier.

### Run and test

Test whether your bot can recognize character patterns that match the pattern used for product order numbers in user input.

```yaml
🧑 i want to cancel my order number TW12345.
🤖 If the pickup time is more than 48 hours from now, you can cancel your order.
🤖 Just to confirm, you want to cancel order TW12345?
🧑 please do
🤖 OK. The order TW12345 is canceled. We hope we get the opportunity to bake a cake for you sometime soon.
```

Now, try it when you don't know the order number.


```yaml
🧑 I want to cancel my order.
🤖 If the pickup time is more than 48 hours from now, you can cancel your order.
🤖 What is the order number?
🧑 I don't know.
🤖 I need the order number to cancel the order for you.
   If you don't know the order number, please call us at 958-234-3456 to cancel over the phone.
```

### Add nodes to clarify order number format

If you do more testing, you might find that the dialog isn't very helpful in scenarios where the user does not remember the order number format. The user might include only the numbers or the letters too, but forget that they are meant to be uppercase. So, it would be a nice touch to give them a hint in such cases, right? If you want to be kind, add another node to the dialog tree that checks for numbers in the user input.

```yaml
- condition: true
  label: ask_order_number
  response: What is the order number?
  followup:
    - condition: entities.order_number
      response: |
          {% set order_number = entities.order_number.literal %}
          OK. The order {{ order_number }} is canceled.
          We hope we get the opportunity to bake a cake for you sometime soon.
# highlight-start
    - condition: message.text|map('int')|select|list|length > 0
      label: clarify_order_number
      response: |
          The correct format for our order numbers is AAnnnnn.
          The A's represents 2 uppercase letters, and the n's represent 5 numbers. <br />
          Do you have an order number in that format?
# highlight-end
    - condition: true
      response: |
          # ...
```

The `message.text|map('int')|select|list|length > 0` is an expression that says if you find one or more numbers in the user input, trigger this response. (TODO: need regex check like `message.text|find('\d+')`).

Add followup node to the `clarify_order_number` node that check for the user's reaction to your clarification.

```yaml
- condition: message.text|map('int')|select|list|length > 0
  label: clarify_order_number
  response: |
      The correct format for our order numbers is AAnnnnn.
      The A's represents 2 uppercase letters, and the n's represent 5 numbers. <br />
      Do you have an order number in that format?
# highlight-start
  followup:
    - condition: true
      response: |
          {% if entities.order_number %}
              {% set order_number = entities.order_number.literal %}
              OK. The order {{ order_number }} is canceled.
              We hope we get the opportunity to bake a cake for you sometime soon.
          {% else %}
              I need the order number to cancel the order for you. <br />
              If you don't know the order number, please call us
              at 958-234-3456 to cancel over the phone.
          {% endif %}
# highlight-end
```

The node's response uses an [if-statement](/design-guides/templates.md#if-conditions) to check if bot recognizes the `entities.order_number`. If so then it cancels the order, otherwise it offers to cancel the order by phone.

Now, when you test, you can provide a set of number or a mix of numbers and text as input, and the dialog reminds you of the correct order number format. You have successfully tested your dialog, found a weakness in it, and corrected it.

## Add the personal touch

If the user shows interest in the bot itself, you want the bot to recognize that curiosity and engage with the user in a more personal way. Add the `intents.about_you` intent and a node that conditions on this intent. In your response, you can ask for the user's name and save it to a `user.name` user variable that you can use elsewhere in the dialog, if available.

### Ask for the user's name

Add an intent `intents.about_you` to recognize the user's interest in the bot.

```yaml
  - name: about_you
    examples:
      - About you
      - Describe yourself
      - Do you have a name?
      - Do you know who you are?
      - How do I set you up?
      - How do you work?
      - How old are you?
      - I want to set up a chatbot for my store
      - Introduce yourself
      - Let's talk about you
      - Tell me about your life
```

Add a node that handles questions about the bot.

```yaml
- condition: intents.about_you
  label: about_you
  response: |
      I am a bot that is designed to answer your questions about the
      Truck Stop Gourmand restaurant. <br />
      What should I call you?
  followup:
    - condition: message.text
      response: |
          {% set user.name = message.text %}
          Hello, {{ user.name }}! It's lovely to meet you.
          How can I help you today?
```

An expression `message.text` captures the user name as it is specified by the user. The captured name is stored in the user variable `user.name` using the [user assignment](/design-reference/jinja#user-assignment):

```django
{% set user.name = message.text %}
```

Unlike slots, user variables can be used not only when discussing the current topic, but also throughout the dialog. If, at run time, the user triggers this node and provides a name, then you will know the user's name. If you know it, you should use it!

### Add personalized greeting

Add an intent to recognize when the user greets the bot.

```yaml
  - name: greetings
    examples:
      - Good morning
      - Hello
      - Hi
```

And a dialog node to greet the user back. If you know the user's name, you should include it in your greeting message. To do so, add if-statement to your response and include a variation of the greeting that includes the user's name.

```yaml
  - condition: intents.greetings
    response: |
        {% if user.name %}
          Good day to you, {{ user.name }}!
        {% else %}
          Good day to you!
        {% endif %}
```

If slots were used to store the user's name, the bot would forget the user's name right after the `about_you` dialog branch ended. But since the name is stored in a user variable, the bot will remember it throughout the dialog.

### Run and test

Test whether your assistant can recognize and save a user's name, and then refer to the user by it later.

```
🧑 Who are you?
🤖 I am a bot that is designed to answer your questions about the Truck Stop Gourmand restaurant.
   What should I call you?
🧑 Jane
🤖 Hello, Jane! It's lovely to meet you. How can I help you today?
```

Your bot saves Jane in the `user.name` variable.

```
🧑 Hello
🤖 Good day to you, Jane!
```

It uses the if-statement block that includes the user's name because the `user.name` variable contains a value at the time that the greeting node is triggered.

You can add an if-statement that conditions on and includes the user's name for any other responses where personalization would add value to the conversation.

## Conclusion

In this example, we have created a complex branching scheme that demonstrates the possibilities of the dialog tree. Another way you can address this type of scenario is to add a node with slots. See the [Reservation Bot](/tutorials/reservation.md) tutorial to learn more about using slots.
