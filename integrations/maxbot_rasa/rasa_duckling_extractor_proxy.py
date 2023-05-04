"""DucklingEntityExtractor subclassing."""
from typing import Any, Dict, List, Text

import rasa.nlu.extractors.duckling_entity_extractor
from rasa.engine.graph import ExecutionContext
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage

original_convert_duckling_format_to_rasa = (
    rasa.nlu.extractors.duckling_entity_extractor.convert_duckling_format_to_rasa
)


def _proxy_convert_duckling_format_to_rasa(
    matches: List[Dict[Text, Any]]
) -> List[Dict[Text, Any]]:
    extracted = original_convert_duckling_format_to_rasa(matches)

    assert len(extracted) == len(matches)
    for m, e in zip(matches, extracted):
        if m.get("latent"):
            e.setdefault("additional_info", {}).update(latent=True)

    return extracted


rasa.nlu.extractors.duckling_entity_extractor.convert_duckling_format_to_rasa = (
    _proxy_convert_duckling_format_to_rasa
)


@DefaultV1Recipe.register(DefaultV1Recipe.ComponentType.ENTITY_EXTRACTOR, is_trainable=False)
class DucklingEntityExtractorProxy(
    rasa.nlu.extractors.duckling_entity_extractor.DucklingEntityExtractor
):
    """DucklingEntityExtractor subclassing."""

    def __init__(self, config: Dict[Text, Any]) -> None:
        """Create the extractor."""
        super().__init__(config)
        parent_keys = self.get_default_config().keys()
        self.__config = {k: v for k, v in config.items() if k not in parent_keys}

    @classmethod
    def create(
        cls,
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
    ) -> rasa.nlu.extractors.duckling_entity_extractor.DucklingEntityExtractor:
        """Create component (see parent class for full docstring)."""
        return cls(config)

    def _payload(self, text: Text, reference_time: int) -> Dict[Text, Any]:
        payload = super()._payload(text, reference_time)
        payload.update(**{k: v for k, v in self.__config.items() if k not in payload})
        return payload
