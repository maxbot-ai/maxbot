# Rasa NLU

You can extend MaxBot with you own NLU (**N**atural-**l**anguage **u**nderstanding) module. MaxBot uses NLU to recognize intents and entities in the user utterances. The `rasa` built-in extension allows you to use an external Rasa Open Source Server as an NLU module for MaxBot.


## Installing Rasa Open Source

Before using the extension, you need to set up Rasa Open Source server that will be ready to accept requests. In the simple case, you can install rasa server with two console commands:

```bash
$ pip3 install rasa[full]
$ rasa init
```

The `rasa init` command will ask you some questions, but you can skip them and leave the default answers.

More information about installing Rasa Open Source can be found in the [official documentation](https://rasa.com/docs/rasa/installation/installing-rasa-open-source/). It will also help you pick the right configuration for your setup.

Now you can start rasa server with the command:

```bash
$ rasa run --enable-api
```

At startup, the server loads the language model which can take a long time. The following message signals that the server is ready to accept requests:

```
INFO     root  - Rasa server is up and running.
```

### Installing Duckling

Rasa uses Duckling to recognize common entities such as dates, times, numbers, and more. In order to take advantage of this features you need to install and run Duckling Server in addition to Rasa. You can find installation instructions in the [official project repository](https://github.com/facebook/duckling).


### Installing `maxbot_rasa`

Rasa integrates with Duckling using the [DucklingEntityExtractor](https://rasa.com/docs/rasa/components/#ducklingentityextractor) component. However, this component does not allow you to use the capabilities of Duckling to recognize so-called latent dates and times. Latent entities are entities that need to be interpreted depending on the dialog context. For example, `at 6 pm` is always a time, but `6` colud be a time if you asked about it before.

The `maxbot_rasa` package fixes this issue. You should install it in the rasa server environment using `pip`:

```
(rasa) $ pip install maxbot_rasa
```

Next, specify `maxbot_rasa.DucklingEntityExtractorProxy` in the rasa pipeline instead of `DucklingEntityExtractor`. This extends the built-in component in the following way.

- You can set additional configuration which will be passed to Duckling in the request.
- You can get the `latent` attribute of the `additional_info` object of entities.

## Configuring MaxBot extension

The `rasa` extension for MaxBot allows you to use Rasa Open Source as an NLU model. You should configure this extension by providing an URL to the rasa server. Rasa server listens on all availabale IPs and port 5005 by default. You can find the actual host and port in the startup output

```
INFO     root  - Starting Rasa server on http://0.0.0.0:5005
```

If rasa server and MaxBot are running on the same host, then you can access Rasa NLU via the loopback address:

```
extensions:
  rasa:
    url: http://127.0.0.1:5005/
```

Optionally, you can adjust the entity recognition threshold. Default value is 0.7. You can decrease this value to get more results but there may be many false positives.

```
extensions:
  rasa:
    url: http://127.0.0.1:5005/
    threshold:
      entity: 0.5
```

When using the `rasa` extension, you do not need to describe intents and entities in MaxBot resources. MaxBot assumes that you have already configured rasa pipelines and trained rasa NLU models. MaxBot simply sends requests to the rasa server to recognize intents and entities.

## Date and time entities

In this section we assume that you have rasa server up and running with the `maxbot_rasa.DucklingEntityExtractorProxy` component in the pipeline and configuration as shown below

```
pipeline:
# - name: DucklingEntityExtractor
  - name: maxbot_rasa.DucklingEntityExtractorProxy
    url: http://100.64.1.2
    dimensions:
    - time
    latent: true
```

There is three kinds of date/time entities:

- `datetime` - recognizes both date and time. Latent version: `latent_datetime`.
- `date` - recognizes date. Latent version: `latent_date`.
- `time` - recognizes time. Latent version: `latent_time`.

All these entities contain an additional `extras` attribute:

- `.extras.granularity` - date/time granularity, required. The value is one of `day`, `hour`, `minute` or `second` (or another value returned by Duckling).
- `.extras.interval` - if the recognized entity is part of a time interval, it indicates the role of the entity in that interval. The value is one of `from`, `to`.
