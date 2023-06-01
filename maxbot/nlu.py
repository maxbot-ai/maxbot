"""Intents and entities recognition using NLU models."""
import logging
import re
import warnings
from functools import cached_property
from itertools import chain
from operator import attrgetter

from .context import EntitiesResult, IntentsResult, RecognizedEntity, RecognizedIntent
from .maxml import fields, validate
from .resources import InlineResources
from .schemas import ResourceSchema

logger = logging.getLogger(__name__)


class IntentSchema(ResourceSchema):
    """Schema for intent resources.

    Intents are purposes or goals that are expressed in a user input.

    For each intent, you must provide a short name (such as `intents.reservation`) and examples of
    utterances that user typically use to indicate their goal.

        IntentSchema(many=True).load('''
          - name: reservation
            examples:
              - i'd like to make a reservation
              - I want to reserve a table for dinner
              - do you have openings for next Wednesday at 7?
              - Is there availability for 4 on Tuesday night?
              - i'd like to come in for brunch tomorrow
        ''')

    The examples are used by NLU component to recognize the same and similar types of utterances and
    map them to the appropriate intent.
    """

    # Intent name.
    name = fields.Str(required=True)

    # Intent examples.
    examples = fields.List(fields.Str(), required=True, validate=validate.Length(min=1))


class EntityValue(ResourceSchema):
    """Schema for entity value resources."""

    # A name used to identify the value.
    name = fields.Str(required=True)

    # A list of phrases with which the value can be mentioned in the user input.
    phrases = fields.List(fields.Str(), load_default=list)

    # A list of a regular expressions that defines the textual pattern of mentions of the value.
    regexps = fields.List(fields.Str(), load_default=list)


class EntitySchema(ResourceSchema):
    r"""Schema for entity resources.

    Entities represent information in the user input that is relevant to the user's purpose.
    Given the `intents.buy_something` you may want to add `entities.product` to extract
    information about the product that the user is interested in.

    NLU component detects entities in the user input by using one of the following methods:

        * Phrases Entity.

        You define an entity (`entities.menu`), and then one or more values for that entity
        (`standard`). For each value, you specify a bunch of phrases with which this
        value can be mentioned in the user input ("standard", "carte du jour", "cuisine").

            EntitySchema(many=True).load('''
              - name: menu
                values:
                  - name: standard
                    phrases: [standard, carte du jour, cuisine]
                  - name: vegetarian
                    phrases: [vegetarian, vegan, plants-only]
                  - name: cake
                    phrases: [cake shop, dessert menu, bakery offerings]
            ''')

        * Regexp Entity.

        You define an entity (`entities.order_number`), and then one or more values for that entity
        (`short_syntax`). For each value, you specify a regular expression that defines the textual
        pattern of mentions of that value type.

            EntitySchema(many=True).load('''
              - name: order_number
                values:
                  - name: short_syntax
                    regexps:
                      - '[A-Z]{2}\\d{5}'
                  - name: full_syntax
                    regexps:
                      - '[DEF]\\-[A-Z]{2}\\d{5}'
            ''')

        * Rule Based Entity.

        Entities that are based on a prebuilt rules. They cover commonly used categories, such as
        `entities.number`, `entities.date`, and `entity.time`. You can just use rule based entities
        without defining them in bot resources.
    """

    # Entity name
    name = fields.Str(required=True)

    # Entity values
    values = fields.List(fields.Nested(EntityValue()), load_default=list)


class SimilarityRecognizer:
    """Recognize intents based on the similarity of sequences of words in utterances.

    Only return intents where the most similar example has a similarity score above a givven
    threshold. Default similarity threshold is 0.7.

    Confidences for intents are calculated by normalaizing similarity scores.
    """

    # Default similarity threshold. The value seems to work good enough.
    default_threshold = 0.7

    def __init__(self, spacy_nlp, threshold=None):
        """Create new class instance.

        :param spacy.Language nlp: Spacy language model.
        :param float|None threshold: Similarity threshold.
        """
        self.spacy_nlp = spacy_nlp
        self.examples, self.labels = [], []
        self.threshold = threshold or self.default_threshold

    @cached_property
    def similarity(self):
        """Return an algorithm that calculates similarity.

        See https://pypi.org/project/textdistance/.
        """
        import textdistance

        return textdistance.cosine.similarity

    def load(self, intents):
        """Load intents resources.

        :param list intents: A list of intents matched the :class:`~IntentSchema`.
        """
        self.examples, self.labels = [], []
        for intent in intents:
            self.examples.extend([self.spacy_nlp.make_doc(e) for e in intent["examples"]])
            self.labels.extend([intent["name"]] * len(intent["examples"]))
        logger.debug("%s similarity based intents loaded", len(intents))

    def _preprocess(self, doc):
        return [t.lower_ for t in doc]

    def __call__(self, doc):
        """Recognize intents.

        :param spacy.tokens.Doc doc: Spacy doc containing the user input.
        :return List[RecognizedIntent]: A list of recognized intents.
        """
        tokens = self._preprocess(doc)
        scores = [self.similarity(tokens, self._preprocess(example)) for example in self.examples]

        max_scores = {}
        for score, label, example in zip(scores, self.labels, self.examples):
            if score > max_scores.get(label, self.threshold):
                max_scores[label] = score
                logger.debug("label '%s' score %s example '%s'", label, score, example.text)

        result = []
        for label, score in max_scores.items():
            confidence = score / len(max_scores)
            result.append(RecognizedIntent(label, confidence))
        return result


class PhraseEntities:
    """Recognize phrase entities."""

    def __init__(self, spacy_nlp):
        """Create new class instance.

        :param spacy.Language nlp: Spacy language model.
        """
        self.spacy_nlp = spacy_nlp
        self.ids = {}
        self._matcher = None

    def load(self, entities):
        """Load phrase entities resources.

        :param list entities: A list of entities matched the :class:`~EntitySchema`.
        """
        self.ids = {}
        self._matcher = None
        if not entities:
            return

        from spacy.matcher import PhraseMatcher

        self._matcher = PhraseMatcher(self.spacy_nlp.vocab, attr="LOWER")
        for entity in entities:
            for value in entity["values"]:
                key = f"{entity['name']}-{value['name']}"
                match_id = self.spacy_nlp.vocab.strings.add(key)
                self.ids[match_id] = (entity["name"], value["name"])
                patterns = list(self.spacy_nlp.pipe(value["phrases"]))
                self._matcher.add(key, patterns)
        logger.debug("%s phrase entities loaded", len([e for e in entities if e["values"]]))

    def __call__(self, doc, utc_time=None):
        """Recognize entities in the given `doc`.

        :param spacy.tokens.Doc doc: Spacy doc containing the user input.
        :param datetime utc_time: Date and time of dialog turn.
        :return Iterable[RecognizedEntity]: Recognized pharse entities.
        """
        if self._matcher:
            for match_id, start, end in self._matcher(doc):
                name, value = self.ids[match_id]
                span = doc[start:end]
                # TODO deal with entities overlap
                yield RecognizedEntity.from_span(span, name, value)


class RegexpEntities:
    """Recognize regexp entities."""

    def __init__(self):
        """Create new class instance."""
        self.regexps = []

    def load(self, entities):
        """Load regexp entities resources.

        :param list entities: A list of entities matched the :class:`~EntitySchema`.
        """
        self.regexps = []
        for entity in entities:
            for value in entity["values"]:
                for regexp in value["regexps"]:
                    self.regexps.append(
                        {
                            "label": entity["name"],
                            "id": value["name"],
                            "pattern": re.compile(regexp),
                        }
                    )
        logger.debug("%s regexp entities loaded", len(self.regexps))

    def __call__(self, doc, utc_time=None):
        """Recognize entities in the given `doc`.

        :param spacy.tokens.Doc doc: Spacy doc containing the user input.
        :param datetime utc_time: Date and time of dialog turn.
        :return Iterable[RecognizedEntity]: Recognized regexps entities.
        """
        for p in self.regexps:
            for match in re.finditer(p["pattern"], doc.text):
                start, end = match.span()
                if start == end:
                    continue
                yield RecognizedEntity(
                    name=p["label"],
                    value=p["id"],
                    literal=doc.text[start:end],
                    start_char=start,
                    end_char=end,
                )


class SpacyMatcherEntities:
    """Recognize rule based entities using spacy matcher.

    Recognizing the following entities: `entities.number`, `entities.email`, `entities.url`.
    """

    builtin_definitions = [
        {"name": "number"},
        {"name": "email"},
        {"name": "url"},
    ]

    def __init__(self, spacy_nlp):
        """Create new class instance.

        :param spacy.Language nlp: Spacy language model.
        """
        self.spacy_nlp = spacy_nlp

    @cached_property
    def matcher(self):
        """Spacy matcher."""
        from spacy.matcher import Matcher

        matcher = Matcher(self.spacy_nlp.vocab)
        matcher.add("number", [[{"LIKE_NUM": True, "OP": "+"}]], greedy="LONGEST")
        matcher.add("email", [[{"LIKE_EMAIL": True}]])
        matcher.add("url", [[{"LIKE_URL": True}]])
        return matcher

    def __call__(self, doc, utc_time=None):
        """Recognize entities in the given `doc`.

        :param spacy.tokens.Doc doc: Spacy doc containing the user input.
        :param datetime utc_time: Date and time of dialog turn.
        :return Iterable[RecognizedEntity]: Recognized entities.
        """
        matches = self.matcher(doc, as_spans=True)
        # does spacy reverse the order while matching greedly?
        matches = sorted(matches, key=attrgetter("start"))
        for span in matches:
            if span.label_ == "number":
                number = self._parse_number(span.text)
                if number is not None:
                    yield RecognizedEntity.from_span(span, "number", number)
            else:
                yield RecognizedEntity.from_span(span)

    def _parse_number(self, text):
        import babel.numbers
        import number_parser

        # try to parse numeric data in a locale-sensitive manner
        for parser in (babel.numbers.parse_number, babel.numbers.parse_decimal):
            try:
                return parser(text, locale="en_US")
            except babel.numbers.NumberFormatError:
                pass
        # try to parse number written in words to an integer
        return number_parser.parse_number(text, language="en")


class DateParserEntities:
    """Recognize rule based entities using "dateparser" library.

    Recognizing the following entities: `entities.date`, `entities.time`.

    Date/Time parsing just for pet projects.
    Use duckling for full featured date/time recognition support.
    """

    builtin_definitions = [
        {"name": "date"},
        {"name": "time"},
    ]

    ddp = None

    def __call__(self, doc, utc_time=None):
        """Recognize entities in the given `doc`.

        :param spacy.tokens.Doc doc: Spacy doc containing the user input.
        :param datetime utc_time: Date and time of dialog turn.
        :return Iterable[RecognizedEntity]: Recognized entities.
        """
        from dateparser import parse
        from dateparser.date import DateDataParser
        from dateparser.search import search_dates

        if self.ddp is None:
            # language autodetection slows down the parser, provide language explicitly
            self.ddp = DateDataParser(languages=["en"], settings={"RETURN_TIME_AS_PERIOD": True})

        # suppress known PytzUsageWarning from dateparser
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            search_dates_settings = {"PREFER_DATES_FROM": "future"}
            if utc_time:
                search_dates_settings["RELATIVE_BASE"] = utc_time

            shift = 0
            results = search_dates(doc.text, languages=["en"], settings=search_dates_settings)
            if results is None:
                return
            for literal, dt in results:
                start_char = doc.text.index(literal, shift)
                end_char = start_char + len(literal)
                shift = end_char
                # a bit tricky way to split date and time parts
                dd = self.ddp.get_date_data(literal)
                if dd.period == "time":
                    if parse(literal, languages=["en"], settings={"REQUIRE_PARTS": ["day"]}):
                        yield RecognizedEntity(
                            "date", dt.date().isoformat(), literal, start_char, end_char
                        )
                    yield RecognizedEntity(
                        "time", dt.time().isoformat(), literal, start_char, end_char
                    )
                else:
                    yield RecognizedEntity(
                        "date", dt.date().isoformat(), literal, start_char, end_char
                    )


class RuleBasedEntities:
    """Compose :class:`~SpacyMatcherEntities` with :class:`~DateParserEntities`.

    Need to manually compose because date/time entities could not overlap with number entities.
    FIXME: need some generic way to resolve overlaps
    """

    def __init__(self, spacy_nlp):
        """Create new class instance.

        :param spacy.Language nlp: Spacy language model.
        """
        self._spacy_nlp = spacy_nlp
        self.dateparser_entities = DateParserEntities()
        self.spacy_matcher_entities = SpacyMatcherEntities(spacy_nlp)

    @property
    def builtin_definitions(self):
        """Get the list of builtin entity definitions.

        :return list:
        """
        rv = []
        rv.extend(self.spacy_matcher_entities.builtin_definitions)
        rv.extend(self.dateparser_entities.builtin_definitions)
        return rv

    def __call__(self, doc, utc_time=None):
        """Recognize entities in the given `doc`.

        :param spacy.tokens.Doc doc: Spacy doc containing the user input.
        :param datetime utc_time: Date and time of dialog turn.
        :return Iterable[RecognizedEntity]: Recognized entities.
        """
        seen_chars = set()
        for entity in self.dateparser_entities(doc, utc_time=utc_time):
            seen_chars.update(range(entity.start_char, entity.end_char))
            yield entity
        for entity in self.spacy_matcher_entities(doc, utc_time=utc_time):
            if entity.name == "number" and (
                entity.start_char in seen_chars or entity.end_char - 1 in seen_chars
            ):
                continue
            yield entity


class Nlu:
    """The component of the bot that orchestrates intents and entities recognizion."""

    # A threshold passed to :meth:`~IntentsResult.resolve`.
    threshold = 0.5

    def __init__(self, spacy_nlp=None):
        """Create new class instance.

        :param spacy.Language spacy_nlp: Spacy language model.
        """
        self._spacy_nlp = spacy_nlp
        self._intent_recognizer = None
        self._entity_recognizers = None
        self._intent_definitinos = None
        self._entity_definitions = None

    # By default we use shared nlp which improves the performance of tests.
    _shared_spacy_nlp = None

    @classmethod
    def _get_shared_spacy_nlp(cls):
        import spacy

        if cls._shared_spacy_nlp is None:
            cls._shared_spacy_nlp = spacy.blank("en")
        return cls._shared_spacy_nlp

    @property
    def spacy_nlp(self):
        """Spacy language model.

        :return spacy.Language
        """
        if self._spacy_nlp is None:
            self._spacy_nlp = self._get_shared_spacy_nlp()
        return self._spacy_nlp

    @property
    def intent_recognizer(self):
        """Access intent recognizer.

        An intent recognizer must be a callable with an argument of type :class:`~spacy.tokens.Doc`
        and return a list of :class:`~RecognizedIntent` objects. Also it must impelemnt a
        `load(intents)` method where `intents` is a list of intent resources that matches
        :class:`~IntentSchema`.

        Default: :class:`~SimilarityRecognizer`.

        :return callable:
        """
        if self._intent_recognizer is None:
            self._intent_recognizer = SimilarityRecognizer(self.spacy_nlp)
        return self._intent_recognizer

    @intent_recognizer.setter
    def intent_recognizer(self, value):
        self._intent_recognizer = value

    @property
    def entity_recognizers(self):
        """Access list of entity recognizers.

        An entity recognizer must be a callable with an argument of type :class:`~spacy.tokens.Doc`
        and return a list of :class:`~RecognizedEntity` objects. Optionally, it can impelemnt a
        `load(entities)` method where `entities` is a list of entity resources that matches
        :class:`~EntitySchema`.

        Default: :class:`~PhraseEntities`, :class:`~RegexpEntities`, :class:`~RuleBasedEntities`.

        :return list[callable]:
        """
        if self._entity_recognizers is None:
            self._entity_recognizers = [
                PhraseEntities(self.spacy_nlp),
                RegexpEntities(),
                RuleBasedEntities(self.spacy_nlp),
            ]
        return self._entity_recognizers

    @entity_recognizers.setter
    def entity_recognizers(self, value):
        self._entity_recognizers = value

    def load_resources(self, resources):
        """Load dialog resources.

        :param Resources resources: Bot resources.
        """
        self._intent_definitinos = resources.load_intents(IntentSchema(many=True))
        if self._intent_definitinos:
            self.intent_recognizer.load(self._intent_definitinos)

        self._entity_definitions = resources.load_entities(EntitySchema(many=True))
        if self._entity_definitions:
            for entity_recognizer in self.entity_recognizers:
                if hasattr(entity_recognizer, "load"):
                    entity_recognizer.load(self._entity_definitions)

    def load_inline_resources(self, source):
        """Load NLU resources from YAML-string.

        :param str source: A YAML-string with resources.
        """
        self.load_resources(InlineResources(source))

    async def __call__(self, message, utc_time=None):
        """Recognize intents and entities for the given message.

        Uses `message['text']` as the user utterance. If the key is missing, it skips recognition.

        :param dict message: A user message that matched :class:`~MessageSchema`.
        :param datetime utc_time: Date and time of dialog turn.
        :return Tuple[IntentsResult, EntitiesResult]: Recognized intents and entities.
        """
        intents, entities = IntentsResult(), EntitiesResult()
        if "text" in message:
            doc = self.spacy_nlp(  # the spacy is callable, so pylint: disable=not-callable
                message["text"]
            )
            intents = IntentsResult.resolve(
                self.intent_recognizer(doc), self.threshold, self.resolve_intent_definitions()
            )
            entities = EntitiesResult.resolve(
                list(
                    chain.from_iterable(
                        recognizer(doc=doc, utc_time=utc_time)
                        for recognizer in self.entity_recognizers
                    )
                ),
                self.resolve_entity_definitions(),
            )
        return intents, entities

    def resolve_intent_definitions(self):
        """Resolve intent definitions for intents result.

        :return dict:
        """
        if self._intent_definitinos is not None:
            return {d["name"]: d for d in self._intent_definitinos}
        return None

    def resolve_entity_definitions(self):
        """Resolve entity definitions for entities result.

        :return dict:
        """
        rv = {}
        if self._entity_definitions is not None:
            rv.update({d["name"]: d for d in self._entity_definitions})
        for recognizer in self.entity_recognizers:
            if hasattr(recognizer, "builtin_definitions"):
                rv.update({d["name"]: d for d in recognizer.builtin_definitions})
        return rv
