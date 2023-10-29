import re
import time
from os import remove, path
from shutil import copy2
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from gensim import corpora, models, similarities
from pykosinus import Conf, Content, ScoringResult, Task
from pykosinus.repositories import scoring as rep


class CosineSimilarity:
    conf: Conf
    _contents: List[Content]

    def __init__(self, collection_name: str, batch_length: Optional[int] = 500) -> None:
        self.conf = Conf.get_config(collection_name, batch_length)

    def push_contents(self, contents: List[Content]) -> "CosineSimilarity":
        self._contents = contents
        return self

    def initialize(self, recreate_index: bool = False) -> "CosineSimilarity":
        rep.init_database(self.conf.sqlite_location)
        open(path.join(self.conf.storage, '.indexing'), 'w').write('')
        Task(target=self._prepare_contents, args=(self._contents,))
        Task(target=self._create_index)
        return self

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
        print(f'got {len(results)} similar contents in {time.time() - st} seconds.')
        return sorted(results, key=lambda obj: obj.score, reverse=True)

    def _prepare_contents(self, contents: List[Content]) -> None:
        try: remove(path.join(self.conf.storage, '.dbprepared'))
        except FileNotFoundError: pass

        st = time.time()
        for contents_batch in self._batch_generator(contents, self.conf.batch_size):
            for content in contents_batch:
                rep.create_base_data(
                    content.content, content.identifier, content.section
                )

        print(f"total '{self.conf.collection}' {rep.count_total_base_data()} base data, finished in {round(time.time() - st, 3)} seconds.")

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

        print(f"total '{self.conf.collection}' {rep.count_total_processed_data()} processed data, finished in {round(time.time() - st, 3)} seconds.")
        open(path.join(self.conf.storage, '.dbprepared'), 'w').write('')

    def _create_index(self) -> Tuple[corpora.Dictionary, models.TfidfModel, similarities.Similarity]:
        if not self._db_prepared:
            time.sleep(3)
            return self._create_index()

        open(path.join(self.conf.storage, '.indexing'), 'w').write('')
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
        remove(path.join(self.conf.storage, '.indexing'))
        return dictionary, tfidf, cosine


    def _get_index(self) -> Tuple[corpora.Dictionary, models.TfidfModel, similarities.Similarity]:
        try:
            dictionary = corpora.Dictionary.load(self.conf.dictionary_location)
            tfidf = models.TfidfModel.load(self.conf.model_location)
            cosine = similarities.Similarity.load(self.conf.cosine_index_location)

            return dictionary, tfidf, cosine
        except FileNotFoundError:
            if not self._indexing and self._db_prepared:
                return self._create_index()
            time.sleep(1)
            return self._get_index()

    @property
    def _db_prepared(self) -> bool:
        return path.exists(path.join(self.conf.storage, '.dbprepared'))

    @property
    def _indexing(self) -> bool:
        return path.exists(path.join(self.conf.storage, 'indexing'))

    @staticmethod
    def _batch_generator(
        data: List[Any], batch_size: int
    ) -> Generator[List[Any], None, None]:
        for i in range(0, len(data), batch_size):
            yield data[i : i + batch_size]


class StreamingCorpus:
    __texts: List[str]
    __dictionary: corpora.Dictionary

    def __init__(self, texts: List[str], dictionary: corpora.Dictionary) -> None:
        self.__texts = texts
        self.__dictionary = dictionary

    def __iter__(
        self,
    ) -> Generator[
        Union[Tuple[List[Tuple[int, int]], Dict[Any, int]], List[Tuple[int, int]]],
        Any,
        None,
    ]:
        for text in self.__texts:
            yield self.__dictionary.doc2bow(text.lower().split())
