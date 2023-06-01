from unittest.mock import Mock

import pytest
import spacy
from freezegun import freeze_time

from maxbot.context import RecognizedEntity, RecognizedIntent
from maxbot.errors import BotError
from maxbot.nlu import (
    DateParserEntities,
    EntitySchema,
    IntentSchema,
    Nlu,
    PhraseEntities,
    RegexpEntities,
    RuleBasedEntities,
    SimilarityRecognizer,
    SpacyMatcherEntities,
)


@pytest.fixture(scope="session")
def spacy_nlp():
    return spacy.blank("en")


def test_similarity_recognizer(spacy_nlp):
    similarity_recognizer = SimilarityRecognizer(spacy_nlp)
    similarity_recognizer.load(
        IntentSchema(many=True).load(
            [
                {
                    "name": "hello",
                    "examples": [
                        "Hello",
                        "hey",
                        "Good morning",
                    ],
                },
                {
                    "name": "how_are_you",
                    "examples": [
                        "how are you",
                        "how are you doing?",
                    ],
                },
            ]
        )
    )

    (intent,) = similarity_recognizer(spacy_nlp("Hello"))
    assert intent.confidence > 0.5
    assert intent.name == "hello"

    (intent,) = similarity_recognizer(spacy_nlp("how are you"))
    assert intent.confidence > 0.5
    assert intent.name == "how_are_you"

    assert not similarity_recognizer(spacy_nlp("i'd like to go to sleep"))

    # reload
    similarity_recognizer.load([])
    assert not similarity_recognizer(spacy_nlp("Hello"))
    assert not similarity_recognizer(spacy_nlp("how are you"))


def test_phrase_entities(spacy_nlp):
    phrase_entities = PhraseEntities(spacy_nlp)
    phrase_entities.load(
        EntitySchema(many=True).load(
            [
                {
                    "name": "menu",
                    "values": [
                        {
                            "name": "standard",
                            "phrases": ["standard menu", "carte du jour", "cuisine"],
                        },
                        {
                            "name": "vegetarian",
                            "phrases": ["vegetarian menu", "vegan", "plants-only"],
                        },
                        {
                            "name": "cake",
                            "phrases": ["cake shop menu", "dessert menu", "bakery offerings"],
                        },
                    ],
                }
            ]
        ),
    )

    (entity,) = phrase_entities(spacy_nlp("i would like something vegan"))
    assert entity.name == "menu"
    assert entity.value == "vegetarian"
    assert entity.literal == "vegan"

    (entity,) = phrase_entities(spacy_nlp("What are your dessert menu?"))
    assert entity.name == "menu"
    assert entity.value == "cake"
    assert entity.literal == "dessert menu"

    (entity,) = phrase_entities(spacy_nlp("Show me the standard menu"))
    assert entity.name == "menu"
    assert entity.value == "standard"
    assert entity.literal == "standard menu"

    # reload
    phrase_entities.load([])
    assert not list(phrase_entities(spacy_nlp("i would like something vegan")))
    assert not list(phrase_entities(spacy_nlp("What are your dessert menu?")))
    assert not list(phrase_entities(spacy_nlp("Show me the standard menu")))


def test_regexp_entities(spacy_nlp):
    regexp_entities = RegexpEntities()
    regexp_entities.load(
        EntitySchema(many=True).load(
            [
                {
                    "name": "order_number",
                    "values": [{"name": "order_syntax", "regexps": ["[A-Z]{2}\\d{5}"]}],
                }
            ]
        ),
    )

    (entity,) = regexp_entities(spacy_nlp("My order number is AB12345"))
    assert entity.name == "order_number"
    assert entity.value == "order_syntax"
    assert entity.literal == "AB12345"

    # reload
    regexp_entities.load([])
    assert not list(regexp_entities(spacy_nlp("My order number is AB12345")))


def test_dateparser_entities(spacy_nlp):
    entity_recognizer = DateParserEntities()

    (entity,) = entity_recognizer(spacy_nlp("2022 May 15"))
    assert entity.name == "date"
    assert entity.value == "2022-05-15"
    assert entity.literal == "2022 May 15"

    (entity,) = entity_recognizer(spacy_nlp("There was 2022 May 15. It was cold."))
    assert entity.name == "date"
    assert entity.value == "2022-05-15"
    assert entity.literal == "2022 May 15"

    assert not list(entity_recognizer(spacy_nlp("not a date")))

    (entity,) = entity_recognizer(spacy_nlp("I will come at 5 pm"))
    assert entity.name == "time"
    assert entity.value == "17:00:00"
    assert entity.literal == "at 5 pm"

    (
        date,
        time,
    ) = entity_recognizer(spacy_nlp("it was February 22, 2022 at 6pm"))
    assert date.name == "date"
    assert date.value == "2022-02-22"
    assert date.literal == "February 22, 2022 at 6pm"
    assert time.name == "time"
    assert time.value == "18:00:00"
    assert time.literal == "February 22, 2022 at 6pm"


@freeze_time("2023-04-08")
def test_dateparser_entities_prefer_future(spacy_nlp):
    entity_recognizer = DateParserEntities()

    # prefer nearest friday from future
    (entity,) = entity_recognizer(spacy_nlp("friday"))
    assert entity.value == "2023-04-14"


def test_spacy_matcher_entities(spacy_nlp):
    entity_recognizer = SpacyMatcherEntities(spacy_nlp)

    two, thirty_seven = entity_recognizer(spacy_nlp("I have two hats and thirty seven coats"))
    assert two.name == "number"
    assert two.value == 2
    assert two.literal == "two"
    assert thirty_seven.name == "number"
    assert thirty_seven.value == 37
    assert thirty_seven.literal == "thirty seven"

    (email,) = entity_recognizer(spacy_nlp("my mail is user@example.com, thats it"))
    assert email.name == "email"
    assert email.value == "user@example.com"
    assert email.literal == "user@example.com"

    (url,) = entity_recognizer(spacy_nlp("go to https://example.com"))
    assert url.name == "url"
    assert url.value == "https://example.com"
    assert url.literal == "https://example.com"


async def test_nlu(spacy_nlp, dialog_stub):
    hello = RecognizedIntent("hello", 0.3)
    goodbye = RecognizedIntent("goodbye", 0.6)

    def intent_recognizer(doc):
        return [hello, goodbye]

    number_1 = RecognizedEntity(name="number", value=1, literal="1", start_char=0, end_char=1)
    number_2 = RecognizedEntity(name="number", value=2, literal="2", start_char=2, end_char=3)
    number_3 = RecognizedEntity(name="number", value=3, literal="three", start_char=3, end_char=8)
    menu_1 = RecognizedEntity(
        name="menu", value="standard", literal="standard menu", start_char=8, end_char=21
    )
    menu_2 = RecognizedEntity(
        name="menu", value="vegetarian", literal="vegan", start_char=23, end_char=28
    )

    entity_recognizer1 = Mock(
        return_value=[number_1, number_2, menu_1, menu_2],
        builtin_definitions=[{"name": "number"}, {"name": "menu"}],
    )

    entity_recognizer2 = Mock(return_value=[number_3], builtin_definitions=[{"name": "number"}])

    nlu = Nlu(spacy_nlp)
    nlu.intent_recognizer = intent_recognizer
    nlu.entity_recognizers = [entity_recognizer1, entity_recognizer2]
    intents, entities = await nlu({"text": "text stub"})

    assert intents.goodbye == goodbye
    assert intents.top == goodbye
    assert intents.ranking == (goodbye, hello)

    assert entities.all_objects == (number_1, number_2, menu_1, menu_2, number_3)
    assert entities.number.all_objects == (number_1, number_2, number_3)
    assert entities.number.all_values == (1, 2, 3)
    assert entities.menu.all_objects == (menu_1, menu_2)
    assert entities.menu.all_values == ("standard", "vegetarian")

    assert entities.number.name == number_1.name
    assert entities.number.value == number_1.value
    assert entities.number.literal == number_1.literal

    assert entities.menu.standard
    assert entities.menu.vegetarian
    assert entities.menu.name == menu_1.name
    assert entities.menu.value == menu_1.value
    assert entities.menu.literal == menu_1.literal


async def test_entities_overlap_datetime(spacy_nlp, dialog_stub):
    nlu = Nlu(spacy_nlp)
    nlu.entity_recognizers = [RuleBasedEntities(spacy_nlp)]
    intents, entities = await nlu(message={"text": "at 5 pm"})
    assert entities.time
    assert not entities.number


async def test_entities_overlap_number(spacy_nlp, dialog_stub):
    nlu = Nlu(spacy_nlp)
    nlu.entity_recognizers = [RuleBasedEntities(spacy_nlp)]
    intents, entities = await nlu({"text": "5 of us"})
    assert not entities.time
    assert entities.number


def test_nlu_defaults(spacy_nlp):
    nlu = Nlu(spacy_nlp)
    assert isinstance(nlu.intent_recognizer, SimilarityRecognizer)
    assert len(nlu.entity_recognizers) == 3
    assert isinstance(nlu.entity_recognizers[0], PhraseEntities)
    assert isinstance(nlu.entity_recognizers[1], RegexpEntities)
    assert isinstance(nlu.entity_recognizers[2], RuleBasedEntities)


def test_nlu_load_resouces(spacy_nlp):
    events = []

    class IR:
        def load(self, intents):
            events.append(("intents", intents))

    class ER1:
        def load(self, entities):
            events.append(("entities 1", entities))

    class ER2:
        def load(self, entities):
            events.append(("entities 2", entities))

    class ER3:
        pass

    nlu = Nlu(spacy_nlp)
    nlu.intent_recognizer = IR()
    nlu.entity_recognizers = [ER1(), ER2(), ER3()]
    nlu.load_inline_resources(
        """
        intents:
          - name: intent1
            examples:
              - intent 1
        entities:
          - name: entity1
            values:
              - name: value1
                phrases:
                  - value 1
    """
    )

    assert len(events) == 3
    assert events[0] == ("intents", [{"name": "intent1", "examples": ["intent 1"]}])
    entities = [
        {"name": "entity1", "values": [{"name": "value1", "phrases": ["value 1"], "regexps": []}]}
    ]
    assert events[1] == ("entities 1", entities)
    assert events[2] == ("entities 2", entities)

    assert nlu.resolve_intent_definitions() == {
        "intent1": {"name": "intent1", "examples": ["intent 1"]}
    }
    assert nlu.resolve_entity_definitions() == {
        "entity1": {
            "name": "entity1",
            "values": [{"name": "value1", "phrases": ["value 1"], "regexps": []}],
        }
    }


@pytest.mark.parametrize(
    "intent,error",
    (
        ({"name": "hello_intent - hello - hi"}, "Missing required field 'examples'."),
        ({"name": "hello_intent - hello - hi", "examples": []}, "Shorter than minimum length 1."),
    ),
)
def test_intent_error(intent, error):
    with pytest.raises(BotError) as excinfo:
        IntentSchema(many=True).load(
            [
                intent,
            ]
        )
    assert str(excinfo.value) == "caused by marshmallow.exceptions.ValidationError: " + error
