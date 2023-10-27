VERSION = "0.0.1"

import hashlib
import os
from typing import Optional

from pydantic import BaseModel, Field


class Conf:
    base_path = os.path.dirname(os.path.abspath(__file__))

    collection: str
    batch_size: int
    sqlite_location: str
    dictionary_location: str
    model_location: str
    index_location: str
    tmp_dictionary_location: str
    tmp_model_location: str
    tmp_index_location: str

    @staticmethod
    def get_config(
        collection_name: str, base_batch_size: Optional[int] = 500
    ) -> "Conf":
        collection_hash = hashlib.md5(collection_name.encode()).hexdigest()
        conf = Conf()

        os.makedirs(os.path.join(conf.base_path, "storage"), exist_ok=True)
        os.makedirs(
            os.path.join(conf.base_path, f"storage/{collection_hash}"), exist_ok=True
        )

        conf.batch_size = base_batch_size or 500
        conf.collection = collection_name
        conf.sqlite_location = os.path.join(
            conf.base_path, f"storage/{collection_hash}/data.sql"
        )
        conf.dictionary_location = os.path.join(
            conf.base_path, f"storage/{collection_hash}/data.dict"
        )
        conf.model_location = os.path.join(
            conf.base_path, f"storage/{collection_hash}/data.model"
        )
        conf.index_location = os.path.join(
            conf.base_path, f"storage/{collection_hash}/data.index"
        )
        conf.tmp_dictionary_location = os.path.join(
            conf.base_path, f"storage/{collection_hash}/.tmp.dict"
        )
        conf.tmp_model_location = os.path.join(
            conf.base_path, f"storage/{collection_hash}/.tmp.model"
        )
        conf.tmp_index_location = os.path.join(
            conf.base_path, f"storage/{collection_hash}/.tmp.index"
        )

        return conf


class Content(BaseModel):
    identifier: Optional[str] = Field(default=None)
    content: str
    section: Optional[str] = Field(default=None)


class ScoringResult(BaseModel):
    identifier: Optional[str] = Field(default=None)
    content: str
    section: str
    similar: str
    score: float
