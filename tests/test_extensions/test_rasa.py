import pytest

from maxbot.errors import BotError
from maxbot.extensions.rasa import RasaExtension

RASA_URL = "http://rasa.pytest/"


@pytest.fixture(scope="function")
def nlu():
    return _create_nlu()


async def test_url_join(respx_mock):
    route = respx_mock.post(RASA_URL + "model/parse").respond(json={})
    await _create_nlu(url=RASA_URL[:-1])(message=dict(text="test"))
    assert route.call_count == 1


async def test_intents_unique_ranking(nlu, respx_mock):
    rasa_answer = {
        "text": "test",
        "intent": {"name": "ask_car_service", "confidence": 0.9998127818107605},
        "entities": [],
        "text_tokens": [[0, 4]],
        "intent_ranking": [
            {"name": "ask_car_service", "confidence": 0.9998127818107605},
            {"name": "reply_yes", "confidence": 0.00016487314132973552},
        ],
    }
    respx_mock.post(RASA_URL + "model/parse").respond(json=rasa_answer)
    intents, entities = await nlu(message=dict(text="test"))
    assert (intents.top.name, intents.top.confidence) == (
        "ask_car_service",
        0.9998127818107605,
    )
    assert [(i.name, i.confidence) for i in intents.ranking] == [
        ("ask_car_service", 0.9998127818107605),
        ("reply_yes", 0.00016487314132973552),
    ]
    assert (entities.proxies, entities.all_objects) == ({}, ())


async def test_latent_time(nlu, respx_mock):
    rasa_answer = {
        "text": "ten",
        "intent": {"name": "ask_car_service", "confidence": 0.9998127818107605},
        "entities": [
            {
                "start": 0,
                "end": 3,
                "text": "ten",
                "value": "2022-09-12T22:00:00.000+01:00",
                "confidence": 1.0,
                "additional_info": {
                    "values": [
                        {
                            "value": "2022-09-12T22:00:00.000+01:00",
                            "grain": "hour",
                            "type": "value",
                        },
                        {
                            "value": "2022-09-13T10:00:00.000+01:00",
                            "grain": "hour",
                            "type": "value",
                        },
                        {
                            "value": "2022-09-13T22:00:00.000+01:00",
                            "grain": "hour",
                            "type": "value",
                        },
                    ],
                    "value": "2022-09-12T22:00:00.000+01:00",
                    "grain": "hour",
                    "type": "value",
                    "latent": True,
                },
                "entity": "time",
                "extractor": "DucklingEntityExtractorProxy",
            }
        ],
        "text_tokens": [[0, 3]],
        "intent_ranking": [],
    }
    respx_mock.post(RASA_URL + "model/parse").respond(json=rasa_answer)
    _, entities = await nlu(message=dict(text="ten"))

    assert [
        (e.name, e.value, e.literal, e.start_char, e.end_char, e.extras)
        for e in entities.all_objects
    ] == [
        (
            "latent_datetime",
            "2022-09-12T22:00:00.000+01:00",
            "ten",
            0,
            3,
            {"granularity": "hour"},
        ),
        ("latent_time", "22:00:00", "ten", 0, 3, {"granularity": "hour"}),
        (
            "latent_datetime",
            "2022-09-13T10:00:00.000+01:00",
            "ten",
            0,
            3,
            {"granularity": "hour"},
        ),
        ("latent_time", "10:00:00", "ten", 0, 3, {"granularity": "hour"}),
        (
            "latent_datetime",
            "2022-09-13T22:00:00.000+01:00",
            "ten",
            0,
            3,
            {"granularity": "hour"},
        ),
    ]


async def test_time(nlu, respx_mock):
    rasa_answer = {
        "text": "at ten",
        "intent": {"name": "ask_car_service", "confidence": 0.9988422989845276},
        "entities": [
            {
                "start": 0,
                "end": 6,
                "text": "at ten",
                "value": "2022-09-12T22:00:00.000+01:00",
                "confidence": 1.0,
                "additional_info": {
                    "values": [
                        {
                            "value": "2022-09-12T22:00:00.000+01:00",
                            "grain": "hour",
                            "type": "value",
                        },
                        {
                            "value": "2022-09-13T10:00:00.000+01:00",
                            "grain": "hour",
                            "type": "value",
                        },
                        {
                            "value": "2022-09-13T22:00:00.000+01:00",
                            "grain": "hour",
                            "type": "value",
                        },
                    ],
                    "value": "2022-09-12T22:00:00.000+01:00",
                    "grain": "hour",
                    "type": "value",
                },
                "entity": "time",
                "extractor": "DucklingEntityExtractorProxy",
            }
        ],
        "text_tokens": [[0, 2], [3, 6]],
        "intent_ranking": [],
    }
    respx_mock.post(RASA_URL + "model/parse").respond(json=rasa_answer)
    _, entities = await nlu(message=dict(text="at ten"))

    assert [
        (e.name, e.value, e.literal, e.start_char, e.end_char, e.extras)
        for e in entities.all_objects
    ] == [
        (
            "datetime",
            "2022-09-12T22:00:00.000+01:00",
            "at ten",
            0,
            6,
            {"granularity": "hour"},
        ),
        ("time", "22:00:00", "at ten", 0, 6, {"granularity": "hour"}),
        (
            "datetime",
            "2022-09-13T10:00:00.000+01:00",
            "at ten",
            0,
            6,
            {"granularity": "hour"},
        ),
        ("time", "10:00:00", "at ten", 0, 6, {"granularity": "hour"}),
        (
            "datetime",
            "2022-09-13T22:00:00.000+01:00",
            "at ten",
            0,
            6,
            {"granularity": "hour"},
        ),
    ]


async def test_date(nlu, respx_mock):
    rasa_answer = {
        "text": "tomorrow",
        "intent": {"name": "reply_yes", "confidence": 0.9997232556343079},
        "entities": [
            {
                "start": 0,
                "end": 8,
                "text": "tomorrow",
                "value": "2022-09-13T00:00:00.000+01:00",
                "confidence": 1.0,
                "additional_info": {
                    "values": [
                        {
                            "value": "2022-09-13T00:00:00.000+01:00",
                            "grain": "day",
                            "type": "value",
                        }
                    ],
                    "value": "2022-09-13T00:00:00.000+01:00",
                    "grain": "day",
                    "type": "value",
                },
                "entity": "time",
                "extractor": "DucklingEntityExtractorProxy",
            }
        ],
        "text_tokens": [[0, 8]],
        "intent_ranking": [],
    }
    respx_mock.post(RASA_URL + "model/parse").respond(json=rasa_answer)
    _, entities = await nlu(message=dict(text="tomorrow"))

    assert [
        (e.name, e.value, e.literal, e.start_char, e.end_char, e.extras)
        for e in entities.all_objects
    ] == [
        (
            "datetime",
            "2022-09-13T00:00:00.000+01:00",
            "tomorrow",
            0,
            8,
            {"granularity": "day"},
        ),
        ("date", "2022-09-13", "tomorrow", 0, 8, {"granularity": "day"}),
    ]


async def test_date_interval(nlu, respx_mock):
    rasa_answer = {
        "text": "weekend",
        "intent": {"name": "reply_no", "confidence": 0.933260977268219},
        "entities": [
            {
                "start": 0,
                "end": 7,
                "text": "weekend",
                "value": {
                    "to": "2022-09-19T00:00:00.000+01:00",
                    "from": "2022-09-16T18:00:00.000+01:00",
                },
                "confidence": 1.0,
                "additional_info": {
                    "values": [
                        {
                            "to": {
                                "value": "2022-09-19T00:00:00.000+01:00",
                                "grain": "hour",
                            },
                            "from": {
                                "value": "2022-09-16T18:00:00.000+01:00",
                                "grain": "hour",
                            },
                            "type": "interval",
                        },
                        {
                            "to": {
                                "value": "2022-09-26T00:00:00.000+01:00",
                                "grain": "hour",
                            },
                            "from": {
                                "value": "2022-09-23T18:00:00.000+01:00",
                                "grain": "hour",
                            },
                            "type": "interval",
                        },
                        {
                            "to": {
                                "value": "2022-10-03T00:00:00.000+01:00",
                                "grain": "hour",
                            },
                            "from": {
                                "value": "2022-09-30T18:00:00.000+01:00",
                                "grain": "hour",
                            },
                            "type": "interval",
                        },
                    ],
                    "to": {
                        "value": "2022-09-19T00:00:00.000+01:00",
                        "grain": "hour",
                    },
                    "from": {
                        "value": "2022-09-16T18:00:00.000+01:00",
                        "grain": "hour",
                    },
                    "type": "interval",
                },
                "entity": "time",
                "extractor": "DucklingEntityExtractorProxy",
            }
        ],
        "text_tokens": [[0, 7]],
        "intent_ranking": [],
    }
    respx_mock.post(RASA_URL + "model/parse").respond(json=rasa_answer)
    _, entities = await nlu(message=dict(text="weekend"))

    assert [
        (e.name, e.value, e.literal, e.start_char, e.end_char, e.extras)
        for e in entities.all_objects
    ] == [
        (
            "datetime",
            "2022-09-16T18:00:00.000+01:00",
            "weekend",
            0,
            7,
            {"granularity": "hour", "interval": "from"},
        ),
        (
            "datetime",
            "2022-09-19T00:00:00.000+01:00",
            "weekend",
            0,
            7,
            {"granularity": "hour", "interval": "to"},
        ),
        (
            "time",
            "18:00:00",
            "weekend",
            0,
            7,
            {"granularity": "hour", "interval": "from"},
        ),
        (
            "time",
            "00:00:00",
            "weekend",
            0,
            7,
            {"granularity": "hour", "interval": "to"},
        ),
        (
            "datetime",
            "2022-09-23T18:00:00.000+01:00",
            "weekend",
            0,
            7,
            {"granularity": "hour", "interval": "from"},
        ),
        (
            "datetime",
            "2022-09-26T00:00:00.000+01:00",
            "weekend",
            0,
            7,
            {"granularity": "hour", "interval": "to"},
        ),
        (
            "datetime",
            "2022-09-30T18:00:00.000+01:00",
            "weekend",
            0,
            7,
            {"granularity": "hour", "interval": "from"},
        ),
        (
            "datetime",
            "2022-10-03T00:00:00.000+01:00",
            "weekend",
            0,
            7,
            {"granularity": "hour", "interval": "to"},
        ),
    ]


async def test_entities_threshold(nlu, respx_mock):
    rasa_answer = {
        "text": "ab xxxxxxxxxxx yyyyyyyyyyyy?",
        "intent": {"name": "ask_car_service", "confidence": 0.9999978542327881},
        "entities": [
            {
                "entity": "car_service_type_14",
                "start": 0,
                "end": 2,
                "confidence_entity": 0.5010738968849182,
                "value": "ab",
                "extractor": "DIETClassifier",
            },
            {
                "entity": "car_service_type_3",
                "start": 3,
                "end": 27,
                "confidence_entity": 0.9976430535316467,
                "value": "xxxxxxxxxxx yyyyyyyyyyyy",
                "extractor": "DIETClassifier",
            },
        ],
        "text_tokens": [[0, 2], [3, 14], [15, 27]],
        "intent_ranking": [{"name": "ask_car_service", "confidence": 0.9999978542327881}],
    }
    respx_mock.post(RASA_URL + "model/parse").respond(json=rasa_answer)
    _, entities = await nlu(message=dict(text="ab xxxxxxxxxxx yyyyyyyyyyyy?"))

    assert [
        (e.name, e.value, e.literal, e.start_char, e.end_char) for e in entities.all_objects
    ] == [
        (
            "car_service_type_3",
            "xxxxxxxxxxx yyyyyyyyyyyy",
            "xxxxxxxxxxx yyyyyyyyyyyy",
            3,
            27,
        ),
    ]


async def test_entities_threshold_05(respx_mock):
    nlu = _create_nlu(entity_threshold=0.5)
    rasa_answer = {
        "text": "ab xxxxxxxxxxx yyyyyyyyyyyy?",
        "intent": {"name": "ask_car_service", "confidence": 0.9999978542327881},
        "entities": [
            {
                "entity": "car_service_type_14",
                "start": 0,
                "end": 2,
                "confidence_entity": 0.5010738968849182,
                "value": "ab",
                "extractor": "DIETClassifier",
            },
            {
                "entity": "car_service_type_3",
                "start": 3,
                "end": 27,
                "confidence_entity": 0.9976430535316467,
                "value": "xxxxxxxxxxx yyyyyyyyyyyy",
                "extractor": "DIETClassifier",
            },
        ],
        "text_tokens": [[0, 2], [3, 14], [15, 27]],
        "intent_ranking": [{"name": "ask_car_service", "confidence": 0.9999978542327881}],
    }
    respx_mock.post(RASA_URL + "model/parse").respond(json=rasa_answer)
    _, entities = await nlu(message=dict(text="ab xxxxxxxxxxx yyyyyyyyyyyy?"))

    assert [
        (e.name, e.value, e.literal, e.start_char, e.end_char) for e in entities.all_objects
    ] == [
        ("car_service_type_14", "ab", "ab", 0, 2),
        (
            "car_service_type_3",
            "xxxxxxxxxxx yyyyyyyyyyyy",
            "xxxxxxxxxxx yyyyyyyyyyyy",
            3,
            27,
        ),
    ]


async def test_requests_error(respx_mock):
    route = respx_mock.post(RASA_URL + "model/parse").respond(status_code=500)
    with pytest.raises(BotError) as excinfo:
        await _create_nlu(url=RASA_URL[:-1])(message=dict(text="test"))
    assert route.call_count == 1
    assert str(excinfo.value) == (
        "caused by httpx.HTTPStatusError: RASA POST model/parse error: "
        "Server error '500 Internal Server Error' for url 'http://rasa.pytest/model/parse'"
        "\nFor more information check: https://httpstatuses.com/500"
    )


async def test_without_text():
    await _create_nlu(url=RASA_URL[:-1])(message=dict())


async def test_unexpected_entity_type(respx_mock):
    rasa_answer = {
        "text": "mytest",
        "intent": {"name": "ask_car_service", "confidence": 0.9998127818107605},
        "entities": [
            {
                "start": 0,
                "end": 6,
                "text": "mytest",
                "value": "2022-09-13T00:00:00.000+01:00",
                "confidence": 1.0,
                "additional_info": {
                    "values": [
                        {
                            "value": "2022-09-13T00:00:00.000+01:00",
                            "grain": "day",
                            "type": "unexpected",
                        }
                    ],
                    "value": "2022-09-13T00:00:00.000+01:00",
                    "grain": "day",
                    "type": "unexpected",
                },
                "entity": "time",
                "extractor": "DucklingEntityExtractorProxy",
            }
        ],
        "text_tokens": [[0, 4]],
        "intent_ranking": [
            {"name": "ask_car_service", "confidence": 0.9998127818107605},
            {"name": "reply_yes", "confidence": 0.00016487314132973552},
        ],
    }
    route = respx_mock.post(RASA_URL + "model/parse").respond(json=rasa_answer)
    with pytest.raises(BotError) as excinfo:
        await _create_nlu(url=RASA_URL[:-1])(message=dict(text="mytest"))
    assert route.call_count == 1
    assert str(excinfo.value) == (
        "Unexpected entity type: {'values': [{'value': "
        "'2022-09-13T00:00:00.000+01:00', 'grain': 'day', 'type': 'unexpected'}], "
        "'value': '2022-09-13T00:00:00.000+01:00', 'grain': 'day', 'type': 'unexpected'}"
    )


def _create_nlu(url=RASA_URL, entity_threshold=None):
    class MockBot:
        pass

    config = """
        url: """
    config += url
    if entity_threshold:
        config += """
        threshold:
          entity: """
        config += str(entity_threshold)

    bot = MockBot()
    RasaExtension(bot, config=RasaExtension.ConfigSchema().loads(config))
    return bot.nlu
