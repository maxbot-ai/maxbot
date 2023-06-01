"""Builtin MaxBot extension: use Rasa NLU as nlu engine."""
import logging
from dataclasses import dataclass
from functools import partial
from typing import Any
from urllib.parse import urljoin

import httpx
from dateutil.parser import isoparse

from ..context import EntitiesResult, IntentsResult, RecognizedEntity, RecognizedIntent
from ..errors import BotError
from ..maxml import Schema, fields
from ..schemas import ResourceSchema

logger = logging.getLogger(__name__)

_TIME_GRANULARITY = frozenset(["hour", "minute", "second"])


@dataclass(frozen=True)
class RecognizedEntityExtras(RecognizedEntity):
    """A child class of the `RecognizedEntity` class with `extras` field."""

    extras: dict[str, Any]


class _Session:
    def __init__(self, url):
        self.__url = url
        self.__impl = httpx.AsyncClient(headers={"accept": "application/json"})

    def __getattr__(self, method):
        return partial(self.__call__, method)

    async def __call__(self, method, url, data=None, json=None):
        logger.debug("%s %s", method.upper(), url)
        try:
            r = await self.__impl.request(method, urljoin(self.__url, url), data=data, json=json)
            r.raise_for_status()
        except httpx.HTTPError as error:
            raise BotError(f"RASA {method.upper()} {url} error: " + str(error)) from error
        logger.debug("finished")
        return r


class _Parsed:
    def __init__(self, parsed, threshold):
        logger.debug(parsed)
        self.parsed = parsed
        self.threshold = threshold

    @property
    def intents(self):
        result = []
        intent = self.parsed.get("intent") or {}
        if intent:
            result.append(self._convert_intent(intent))
        result += [
            self._convert_intent(i)
            for i in self.parsed.get("intent_ranking", [])
            if i["name"] != intent.get("name")
        ]
        return result

    def _convert_intent(self, intent):
        return RecognizedIntent(intent["name"], intent["confidence"])

    @property
    def entities(self):
        recognized = []
        for e in self.parsed.get("entities", []):
            if not self._check_entity(e):
                continue
            for r in self._iter_entities(e):
                if r not in recognized:
                    recognized.append(r)
        return recognized

    def _check_entity(self, entity):
        threshold = self.threshold.get("entity")
        if threshold and threshold > entity.get("confidence_entity", threshold):
            return False
        return True

    def _iter_entities(self, entity):
        name = entity["entity"]
        start, end = entity["start"], entity["end"]
        literal = self.parsed["text"][start:end]

        if name == "time":
            yield from self._iter_time_entities(entity, literal, start, end)
        else:
            yield RecognizedEntity(name, entity["value"], literal, start, end)

    def _iter_time_entities(self, entity, literal, start, end):
        additional_info = entity["additional_info"]
        prefix = "latent_" if additional_info.get("latent") else ""

        def _iter(obj, getter):
            def _recognized(obj, interval=None):
                name, value = getter(obj)
                extras = {"granularity": obj["grain"]}
                if interval:
                    extras.update(interval=interval)
                return RecognizedEntityExtras(prefix + name, value, literal, start, end, extras)

            if obj["type"] == "value":
                yield _recognized(obj)
            elif obj["type"] == "interval":
                yield _recognized(obj["from"], "from")
                yield _recognized(obj["to"], "to")
            else:
                raise BotError(f"Unexpected entity type: {obj}")

        yield from _iter(additional_info, _Parsed._getter_datetime)

        for v in additional_info.get("values", []):
            yield from _iter(v, _Parsed._getter_datetime)
            yield from _iter(v, _Parsed._getter_date_or_time)

    @staticmethod
    def _getter_datetime(obj):
        return "datetime", obj["value"]

    @staticmethod
    def _getter_date_or_time(obj):
        if obj["grain"] in _TIME_GRANULARITY:
            return "time", isoparse(obj["value"]).time().isoformat()
        return "date", isoparse(obj["value"]).date().isoformat()


class _Nlu:
    def __init__(self, url, threshold):
        self.session = _Session(url)
        self.threshold = threshold
        logger.debug("threshold = %s", self.threshold)

    async def __call__(self, message, utc_time=None):
        text = message.get("text")
        if not text:
            return IntentsResult(), EntitiesResult()

        r = await self.session.post("model/parse", json={"text": text})
        parsed = _Parsed(r.json(), self.threshold)
        return IntentsResult.resolve(parsed.intents), EntitiesResult.resolve(parsed.entities)


class _Threshold(Schema):
    entity = fields.Float(load_default=0.7)


class RasaExtension:
    """Extension class."""

    class ConfigSchema(ResourceSchema):
        """Extension configuration schema."""

        url = fields.Url(required=True)
        threshold = fields.Nested(_Threshold(), load_default=_Threshold().load({}))

    def __init__(self, builder, config):
        """Extension entry point.

        :param BotBuilder builder: MaxBot builder.
        :param dict config: Extension configuration.
        """
        builder.nlu = _Nlu(config["url"], config.get("threshold"))
