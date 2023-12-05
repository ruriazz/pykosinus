import contextlib
import pickle
import time
from copy import deepcopy
from typing import List, Optional, Tuple

import redis
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

    def _get_similarity(self, indexs, keyword, threshold, results) -> None:
        dictionary = indexs[0]
        tfidf = indexs[1]
        cosine = indexs[2]

        processed_key = keyword.strip().lower().split()
        key_vector = dictionary.doc2bow(processed_key)
        key_vector_tfidf = tfidf[key_vector]
        sims = cosine[key_vector_tfidf]

        for i, sim in enumerate(sims):
            sim = float(sim)
            if sim >= threshold:
                if content := self.get_scoring_content(i):
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

    def create_index(self, contents: List[Content], update: bool = False) -> None:
        st = time.time()
        scoring_content = self.compile_content(contents)

        if update:
            if not self.is_filling():
                return log.warning("CosineSimilarity.create_index cancel for updating.")

            if not (_ := self.get_index(True, 10)):
                return log.warning("CosineSimilarity.create_index cancel for updating.")

            _scoring_content = self.dump_all_scoring_content() or []
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
        pipeline = self.conf.redis_client.pipeline()
        pipeline.set(self.conf.dictionary_redis_key, pickle.dumps(dictionary))
        pipeline.set(self.conf.model_redis_key, pickle.dumps(tfidf))
        pipeline.set(self.conf.cosine_index_redis_key, pickle.dumps(cosine))

        self.save_scoring_content(scoring_content, pipeline)
        pipeline.execute()
        self.filling(True)
        log.debug(
            f"save CosineSimilarity model finished in {round(time.time() - st, 3)} seconds."
        )

    def get_index(
        self, waiting: bool = False, retry: int = 5
    ) -> Optional[
        Tuple[corpora.Dictionary, models.TfidfModel, similarities.Similarity]
    ]:
        result = None
        with contextlib.suppress(FileNotFoundError, pickle.UnpicklingError):
            dictionary = None
            if data := self.conf.redis_client.get(self.conf.dictionary_redis_key):
                dictionary = pickle.loads(data)

            tfidf = None
            if data := self.conf.redis_client.get(self.conf.model_redis_key):
                tfidf = pickle.loads(data)

            cosine = None
            if data := self.conf.redis_client.get(self.conf.cosine_index_redis_key):
                cosine = pickle.loads(data)

            if cosine and tfidf and dictionary:
                result = (dictionary, tfidf, cosine)
        if not result and waiting and retry > 0:
            time.sleep(1)
            return self.get_index(waiting, retry - 1)
        if retry <= 0 and not result:
            log.warning(
                "CosineSimilarity.get_index was not executed because it waited too long."
            )
        return result

    def compile_content(
        self, contents: List[Content], include_whitespace: bool = True
    ) -> List[ScoringContent]:
        results = []
        for content in contents:
            if text := content.content.strip().lower():
                sc = ScoringContent(
                    identifier=content.identifier,
                    original=content.content,
                    content=text if include_whitespace else text.replace(" ", ""),
                    section=content.section,
                    score=0,
                )
                results.append(sc)
        return results

    def save_scoring_content(
        self,
        contents: List[ScoringContent],
        pipeline: Optional[redis.client.Pipeline] = None,
    ) -> None:
        force_save = not pipeline
        pipeline = pipeline or self.conf.redis_client.pipeline()

        pipeline.set(
            f"{self.conf.score_contents_redis_pattern}_master", pickle.dumps(contents)
        )
        for i, content in enumerate(contents):
            key = f"{self.conf.score_contents_redis_pattern}.{i}"
            pipeline.set(key, pickle.dumps(content))

        if force_save:
            pipeline.execute()

    def dump_all_scoring_content(self) -> Optional[List[ScoringContent]]:
        if data := self.conf.redis_client.get(
            f"{self.conf.score_contents_redis_pattern}_master"
        ):
            return pickle.loads(data)

    def get_scoring_content(self, index: int) -> Optional[ScoringContent]:
        if data := self.conf.redis_client.get(
            f"{self.conf.score_contents_redis_pattern}.{index}"
        ):
            with contextlib.suppress(Exception):
                return pickle.loads(data)

    def filling(self, end: bool = False) -> None:
        if end:
            self.conf.redis_client.delete(
                f"{self.conf.collection_config_key}.filling.gensim"
            )
            return
        self.conf.redis_client.set(
            f"{self.conf.collection_config_key}.filling.gensim",
            ":filling gensim:",
            ex=300,
        )

    def is_filling(self, retry: int = 100) -> bool:
        while (
            _ := self.conf.redis_client.get(
                f"{self.conf.collection_config_key}.filling.gensim"
            )
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
