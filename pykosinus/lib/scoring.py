import time
from typing import List, Optional

from pykosinus import Content, ScoringContent, log
from pykosinus.lib import BaseScoring
from pykosinus.lib.cosine_similarity import CosineSimilarity
from pykosinus.lib.fuzzy_match import FuzzyMatch
from pykosinus.lib.spellcheck import SpellCheck


class TextScoring(BaseScoring):
    _contents: List[Content]
    cosine_similarity: CosineSimilarity
    fuzzy_match: FuzzyMatch
    spell: SpellCheck

    def __init__(
        self,
        collection_name: str,
        fuzz: bool = False,
        spellcheck: bool = True,
        batch_length: Optional[int] = 500,
    ) -> None:
        super().__init__(collection_name, batch_length)
        self._contents = []

        self.cosine_similarity = CosineSimilarity(collection_name, batch_length)
        if fuzz:
            self.fuzzy_match = FuzzyMatch(collection_name, batch_length)

        if spellcheck:
            self.spell = SpellCheck(collection_name)

    def search(
        self, keyword: str, threshold: float = 0.5, spelling_correction: bool = True
    ) -> List[ScoringContent]:
        st = time.time()
        if hasattr(self, "spell") and spelling_correction:
            keyword = self.spell.correction(keyword)

        results = self.cosine_similarity.search(keyword, threshold)

        if hasattr(self, "fuzzy_match"):
            for content in self.fuzzy_match.search(keyword, threshold):
                if not (
                    _ := next(
                        (c for c in results if c.identifier == content.identifier),
                        None,
                    )
                ):
                    results.append(content)
        results = sorted(results, key=lambda obj: obj.score, reverse=True)
        log.info(
            f"got {len(results)} total similar contents with keyword '{keyword}' in {round(time.time() - st, 3)} seconds."
        )
        return results

    def push_contents(self, contents: List[Content]) -> "TextScoring":
        self._contents = contents
        return self

    def initialize(self) -> "TextScoring":
        self.cosine_similarity.create_index(self._contents)
        if hasattr(self, "fuzzy_match"):
            self.fuzzy_match.create_index(self._contents)

        if hasattr(self, "spell"):
            self.spell.create_dictionary([i.content for i in self._contents])

        return self

    def update(self, content: List[Content]) -> "TextScoring":
        self.cosine_similarity.create_index(content, True)
        if hasattr(self, "fuzzy_match"):
            self.fuzzy_match.create_index(content, True)

        if hasattr(self, "spell"):
            self.spell.create_dictionary([i.content for i in content], True)
        return self

    def add_spell_dictionary(self, dictionary: List[str]) -> "TextScoring":
        if hasattr(self, "spell"):
            self.spell.create_dictionary(dictionary, True)
        return self
