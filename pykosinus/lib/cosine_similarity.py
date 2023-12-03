import contextlib
import pickle
import time
from copy import deepcopy
from os import path, remove
from typing import List, Optional, Tuple

from gensim import corpora, models, similarities

from pykosinus import Content, ScoringContent, log
from pykosinus.lib import BaseScoring


class CosineSimilarity(BaseScoring):
    _contents: List[Content]

    def search(self, keyword: str, threshold: float = 0.4) -> List[ScoringContent]:
        st = time.time()
        results = []
        if indexs := self.get_index():
            self._get_similarity(indexs, keyword, threshold, results)
        log.info(
            f"got {len(results)} CosineSimilarity similar contents with keyword '{keyword}' in {round(time.time() - st, 3)} seconds."
        )
        return results

    def _get_similarity(self, indexs, keyword, threshold, results):
        scoring_content = indexs[0]
        dictionary = indexs[1]
        tfidf = indexs[2]
        cosine = indexs[3]

        processed_key = keyword.strip().lower().split()
        key_vector = dictionary.doc2bow(processed_key)
        key_vector_tfidf = tfidf[key_vector]
        sims = cosine[key_vector_tfidf]

        for i, sim in enumerate(sims):
            sim = float(sim)
            if sim >= threshold:
                content = scoring_content[i]
                content.score = sim

                if existing_content := next(
                    (c for c in results if c.identifier == content.identifier),
                    None,
                ):
                    if content.score > existing_content.score:
                        existing_content.score = content.score
                        existing_content.content = content.content
                        existing_content.section = content.section
                        existing_content.original = content.original
                else:
                    results.append(content)

    def create_index(self, contents: List[Content], update: bool = False):
        st = time.time()
        scoring_content = self.compile_content(contents)

        if update:
            if not self.is_filling():
                return log.warning("CosineSimilarity.create_index cancel for updating.")

            if not (indexs := self.get_index(True, 10)):
                return log.warning("CosineSimilarity.create_index cancel for updating.")

            _scoring_content = indexs[0]
            for content in deepcopy(scoring_content):
                if content not in _scoring_content:
                    _scoring_content.append(content)
            scoring_content = _scoring_content
        log.debug(f"total CosineSimilarity scoring content {len(scoring_content)}")
        objects_generator = (str(i.content) for i in scoring_content)
        objects_list = list(objects_generator)
        dictionary = corpora.Dictionary((text.split() for text in objects_list))
        corpus = [dictionary.doc2bow(text.split()) for text in objects_list]
        tfidf = models.TfidfModel(corpus)
        cosine = similarities.Similarity(
            None, tfidf[corpus], num_features=len(dictionary)
        )
        log.debug(
            f"generate CosineSimilarity model finish in {round(time.time() - st, 3)} seconds."
        )

        st = time.time()
        if not self.is_filling():
            return

        self.filling()
        with open(self.conf.score_contents, "wb") as file:
            pickle.dump(scoring_content, file)
        dictionary.save(self.conf.dictionary_location)
        tfidf.save(self.conf.model_location)
        cosine.save(self.conf.cosine_index_location)
        self.filling(True)
        log.debug(
            f"save CosineSimilarity model finished in {round(time.time() - st, 3)} seconds."
        )

    def get_index(
        self, waiting: bool = False, retry: int = 5
    ) -> Optional[
        Tuple[
            List[ScoringContent],
            corpora.Dictionary,
            models.TfidfModel,
            similarities.Similarity,
        ]
    ]:
        result = None
        with contextlib.suppress(FileNotFoundError):
            with open(self.conf.score_contents, "rb") as file:
                scoring_content: List[ScoringContent] = pickle.load(file)
            dictionary = corpora.Dictionary.load(self.conf.dictionary_location)
            tfidf = models.TfidfModel.load(self.conf.model_location)
            cosine = similarities.Similarity.load(self.conf.cosine_index_location)
            result = (scoring_content, dictionary, tfidf, cosine)
        if not result and waiting and retry > 0:
            time.sleep(1)
            return self.get_index(waiting, retry - 1)
        if retry <= 0 and not result:
            log.warning(
                "CosineSimilarity.get_index was not executed because it waited too long."
            )
        return result

    def filling(self, end: bool = False) -> None:
        if end:
            with contextlib.suppress(FileNotFoundError):
                remove(path.join(self.conf.storage, ":filling gensim:"))
            return
        open(path.join(self.conf.storage, ":filling gensim:"), "wb").write(b"")

    def is_filling(self, retry: int = 100) -> bool:
        while (
            _ := path.exists(path.join(self.conf.storage, ":filling gensim:"))
            and retry > 0
        ):
            log.info("CosineSimilarity.create_index wait process to run ..")
            retry -= 1
            time.sleep(1.5)
        if retry == 0:
            log.warning(
                "CosineSimilarity.create_index was not executed because it waited too long."
            )
            return False
        return True
