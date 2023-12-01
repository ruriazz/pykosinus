VERSION = "0.1.7"

import hashlib
import logging
import os
from typing import Any, Callable, Iterable, Optional

from pydantic import BaseModel, Field

log = logging.getLogger("pykosinus-0.1.4")


class Conf:
    base_path = os.path.dirname(os.path.abspath(__file__))

    collection: str
    storage: str
    batch_size: int
    sqlite_location: str
    dictionary_location: str
    model_location: str
    cosine_index_location: str
    sparse_index_location: str
    pickle_index_location: str
    tmp_dictionary_location: str
    tmp_model_location: str
    tmp_cosine_index_location: str
    tmp_sparse_index_location: str
    tmp_pickle_index_location: str

    @staticmethod
    def get_config(collection_name: str, base_batch_size: Optional[int] = 50) -> "Conf":
        collection_hash = hashlib.md5(collection_name.encode()).hexdigest()
        conf = Conf()

        base_path = conf.base_path
        if base_path_env := os.getenv("PYKOSINUS_BASE_PATH"):
            base_path = os.path.join(os.getcwd(), base_path_env)
            os.makedirs(base_path, exist_ok=True)

        conf.storage = os.path.join(base_path, f"storage/{collection_hash}")
        os.makedirs(os.path.join(base_path, "storage"), exist_ok=True)
        os.makedirs(conf.storage, exist_ok=True)

        conf.batch_size = base_batch_size or 500
        conf.collection = collection_name
        conf.sqlite_location = os.path.join(base_path, conf.storage, "model.sql")
        conf.dictionary_location = os.path.join(base_path, conf.storage, "model.dict")
        conf.model_location = os.path.join(base_path, conf.storage, "model.model")
        conf.cosine_index_location = os.path.join(
            base_path, conf.storage, "model.cosine.index"
        )
        conf.sparse_index_location = os.path.join(
            base_path, conf.storage, "model.sparse.index"
        )
        conf.pickle_index_location = os.path.join(
            base_path, conf.storage, "model.pickle"
        )
        conf.tmp_dictionary_location = os.path.join(
            base_path, conf.storage, ".tmp.dict"
        )
        conf.tmp_model_location = os.path.join(base_path, conf.storage, ".tmp.model")
        conf.tmp_cosine_index_location = os.path.join(
            base_path, conf.storage, ".tmp.cosine.index"
        )
        conf.tmp_sparse_index_location = os.path.join(
            base_path, conf.storage, ".tmp.sparse.index"
        )
        conf.tmp_pickle_index_location = os.path.join(
            base_path, conf.storage, ".tmp.model.pickle"
        )

        return conf


class Content(BaseModel):
    identifier: str
    content: str
    section: Optional[str] = Field(default=None)


class ScoringResult(BaseModel):
    identifier: str
    content: str
    section: Optional[str] = Field(default=None)
    similar: str
    score: float


class Task:
    def __init__(
        self,
        target: Callable[..., object],
        args: Iterable[Any] = (),
        name: Optional[str] = None,
        **_kwargs,
    ) -> None:
        # threading.Thread(target=target, args=args, name=name, *_args, **_kwargs).start()

        if name:
            log.info(f"New {name} pykosinus task received.")
        else:
            log.info("New default pykosinus task received.")

        target(*args, **_kwargs)
