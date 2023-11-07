import contextlib
import pickle
import re
import time
from os import path, remove
from shutil import copy2
from typing import Any, Generator, List, Optional, Tuple

from fuzzywuzzy import fuzz
from gensim import corpora, models, similarities

from pykosinus import Conf, Content, ScoringResult, Task
from pykosinus.repositories import scoring as rep


class __BaseScoring:
    conf: Conf

    def __init__(self, collection_name: str, batch_length: Optional[int] = 500) -> None:
        self.conf = Conf.get_config(collection_name, batch_length)

    def indexed(self, start: bool = True) -> None:
        if start:
            open(path.join(self.conf.storage, ".indexed"), "w").write("")
            return
        with contextlib.suppress(FileNotFoundError):
            remove(path.join(self.conf.storage, ".indexed"))

    def db_prepared(self, start: bool = True) -> None:
        if start:
            open(path.join(self.conf.storage, ".dbprepared"), "w").write("")
            return
        with contextlib.suppress(FileNotFoundError):
            remove(path.join(self.conf.storage, ".dbprepared"))

    def partial_indexed(self, start: bool = True) -> None:
        if start:
            open(path.join(self.conf.storage, ".part.indexed"), "w").write("")
            return
        with contextlib.suppress(FileNotFoundError):
            remove(path.join(self.conf.storage, ".part.indexed"))

    @property
    def is_db_prepared(self) -> bool:
        return path.exists(path.join(self.conf.storage, ".dbprepared"))

    @property
    def is_indexed(self) -> bool:
        return path.exists(path.join(self.conf.storage, ".indexed"))

    @property
    def is_partial_indexed(self) -> bool:
        return path.exists(path.join(self.conf.storage, ".part.indexed"))

    @staticmethod
    def _batch_generator(
        data: List[Any], batch_size: int
    ) -> Generator[List[Any], None, None]:
        for i in range(0, len(data), batch_size):
            yield data[i : i + batch_size]


class _CosineSimilarity(__BaseScoring):
    _contents: List[Content]

    def search(self, keyword: str, threshold: float = 0.5) -> List[ScoringResult]:
        st = time.time()
        processed_key = keyword.strip().lower().split()
        dictionary, tfidf, cosine = self._get_index()
        key_vector = dictionary.doc2bow(processed_key)
        key_vector_tfidf = tfidf[key_vector]
        sims = cosine[key_vector_tfidf]

        id_scores = {}
        for i, sim in enumerate(sims):
            sim = float(sim)
            if sim >= threshold:
                data = rep.get_processed_data_by_id(i + 1)
                result = {
                    "identifier": data.base_data.identifier,
                    "content": data.base_data.content,
                    "section": data.base_data.section,
                    "similar": data.content,
                    "score": sim,
                }
                if result["identifier"] in id_scores:
                    if sim > id_scores[result["identifier"]]["score"]:
                        id_scores[result["identifier"]] = result
                else:
                    id_scores[result["identifier"]] = result

        results = [ScoringResult(**result) for result in list(id_scores.values())]
        print(f"got {len(results)} similar contents in {time.time() - st} seconds.")
        return sorted(results, key=lambda obj: obj.score, reverse=True)

    def _create_index(
        self,
    ) -> Tuple[corpora.Dictionary, models.TfidfModel, similarities.Similarity]:
        if not self.is_db_prepared:
            time.sleep(3)
            return self._create_index()

        self.indexed()
        objects_generator = (str(i.content) for i in rep.get_all_processed_data())
        objects_list = list(objects_generator)

        dictionary = corpora.Dictionary((text.split() for text in objects_list))
        corpus = [dictionary.doc2bow(text.split()) for text in objects_list]

        tfidf = models.TfidfModel(corpus)
        cosine = similarities.Similarity(
            None, tfidf[corpus], num_features=len(dictionary)
        )

        dictionary.save(self.conf.tmp_dictionary_location)
        tfidf.save(self.conf.tmp_model_location)
        cosine.save(self.conf.tmp_cosine_index_location)

        copy2(self.conf.tmp_dictionary_location, self.conf.dictionary_location)
        copy2(self.conf.tmp_model_location, self.conf.model_location)
        copy2(self.conf.tmp_cosine_index_location, self.conf.cosine_index_location)

        remove(self.conf.tmp_dictionary_location)
        remove(self.conf.tmp_model_location)
        remove(self.conf.tmp_cosine_index_location)

        if self.is_partial_indexed:
            self.indexed(False)
            self.partial_indexed(False)
        else:
            self.partial_indexed()

        return dictionary, tfidf, cosine

    def _get_index(
        self,
    ) -> Tuple[corpora.Dictionary, models.TfidfModel, similarities.Similarity]:
        try:
            dictionary = corpora.Dictionary.load(self.conf.dictionary_location)
            tfidf = models.TfidfModel.load(self.conf.model_location)
            cosine = similarities.Similarity.load(self.conf.cosine_index_location)

            return dictionary, tfidf, cosine
        except FileNotFoundError:
            if not self.is_indexed and self.is_db_prepared:
                return self._create_index()
            time.sleep(1)
            return self._get_index()


class _FuzzyMatch(__BaseScoring):
    def search(self, keyword: str, threshold: float = 0.5) -> List[ScoringResult]:
        if threshold < 0.7:
            threshold += 0.35

        st = time.time()
        list_object = self._get_index()
        id_scores = {}
        for word in list_object:
            sim = float(fuzz.ratio(word, keyword.strip().lower()) / 100)
            if sim < 1:
                sim -= 0.09

            if sim >= threshold:
                for data in rep.get_processed_data_by_content(word):
                    result = {
                        "identifier": data.base_data.identifier,
                        "content": data.base_data.content,
                        "section": data.base_data.section,
                        "similar": data.content,
                        "score": sim,
                    }
                    if result["identifier"] in id_scores:
                        if sim > id_scores[result["identifier"]]["score"]:
                            id_scores[result["identifier"]] = result
                    else:
                        id_scores[result["identifier"]] = result

        results = [ScoringResult(**result) for result in list(id_scores.values())]
        print(f"got {len(results)} similar contents in {time.time() - st} seconds.")
        return sorted(results, key=lambda obj: obj.score, reverse=True)

    def _create_index(self) -> List[str]:
        if not self.is_db_prepared:
            time.sleep(3)
            return self._create_index()

        self.indexed()
        objects_generator = (
            str(i.content)
            for i in rep.get_all_processed_data()
            if len(str(i.content).strip().split()) == 1
        )
        objects_list = list(objects_generator)

        with open(self.conf.tmp_pickle_index_location, "wb") as f:
            pickle.dump(objects_list, f)
            copy2(self.conf.tmp_pickle_index_location, self.conf.pickle_index_location)
            remove(self.conf.tmp_pickle_index_location)

        if self.is_partial_indexed:
            self.indexed(False)
            self.partial_indexed(False)
        else:
            self.partial_indexed()

        return objects_list

    def _get_index(self) -> List[str]:
        try:
            with open(self.conf.pickle_index_location, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            if not self.is_indexed and self.is_db_prepared:
                return self._create_index()
            time.sleep(1)
            return self._get_index()
        except EOFError:
            return []


class TextScoring(__BaseScoring):
    _contents: List[Content]
    cosine_similarity: _CosineSimilarity
    fuzzy_match: _FuzzyMatch

    def __init__(self, collection_name: str, batch_length: Optional[int] = 500) -> None:
        super().__init__(collection_name, batch_length)
        self._contents = []

        self.cosine_similarity = _CosineSimilarity(collection_name, batch_length)
        self.fuzzy_match = _FuzzyMatch(collection_name, batch_length)

    def push_contents(self, contents: List[Content]) -> "TextScoring":
        self._contents += contents
        return self

    def initialize(self) -> "TextScoring":
        rep.init_database(self.conf.sqlite_location)
        self.indexed()

        # init contents
        Task(target=self._prepare_contents, args=(self._contents,))

        # init cosine similarity model
        Task(target=self.cosine_similarity._create_index)

        # Init fuzzy match model
        Task(target=self.fuzzy_match._create_index)

        return self

    def search(self, keyword: str, threshold: float = 0.5) -> List[ScoringResult]:
        results = self.cosine_similarity.search(keyword, threshold)
        if len(keyword.strip().split()) == 1:
            results += self.fuzzy_match.search(keyword, threshold)
        unique_results = []
        seen_identifiers = set()

        for result in results:
            if result.identifier not in seen_identifiers:
                unique_results.append(result)
                seen_identifiers.add(result.identifier)

        return sorted(unique_results, key=lambda obj: obj.score, reverse=True)

    def _prepare_contents(self, contents: List[Content]) -> None:
        self.db_prepared(False)

        st = time.time()
        for contents_batch in self._batch_generator(contents, self.conf.batch_size):
            for content in contents_batch:
                rep.create_base_data(
                    content.content, content.identifier, content.section
                )

        print(
            f"total '{self.conf.collection}' {rep.count_total_base_data()} base data, finished in {round(time.time() - st, 3)} seconds."
        )

        st = time.time()
        for offset in range(0, rep.count_total_base_data(), self.conf.batch_size):
            base_data_batch = rep.get_all_base_data(
                offset=offset, size=self.conf.batch_size
            )
            for data in base_data_batch:
                content = str(data.content).lower()
                rep.create_processed_data(base_data=data, content=content)

                clear_content = re.sub(r"[^\w\s]", "", content)
                rep.create_processed_data(base_data=data, content=clear_content)

        print(
            f"total '{self.conf.collection}' {rep.count_total_processed_data()} processed data, finished in {round(time.time() - st, 3)} seconds."
        )
        self.db_prepared()
