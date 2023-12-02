import contextlib
import re
from copy import deepcopy
from os import path, remove
from typing import Any, Generator, List, Optional

from pykosinus import Conf, Constant, Content, ScoringContent


class BaseScoring:
    conf: Conf

    def compile_content(
        self, contents: List[Content], include_whitespace: bool = True
    ) -> List[ScoringContent]:
        results = []

        for content in contents:
            _results = []
            if text := content.content.strip().lower():
                sc = ScoringContent(
                    identifier=content.identifier,
                    original=content.content,
                    content=text if include_whitespace else text.replace(" ", ""),
                    section=content.section,
                    score=0,
                )
                _results.append(sc)

                def add_formating(
                    regex: str, replacement: str = ""
                ) -> List[ScoringContent]:
                    if clean_text := re.sub(regex, replacement, text).strip():
                        if not include_whitespace:
                            clean_text = clean_text.replace(" ", "")

                        if all(clean_text != result.content for result in _results):
                            _sc = deepcopy(sc)
                            _sc.content = clean_text
                            return [_sc]
                    return []

                _results += add_formating(Constant.ALL_SPECIAL_CHAR_REGEX)
                _results += add_formating(Constant.SPECIAL_CHAR_REGEX)
                _results += add_formating(Constant.WHITESPACE_REPLACEMENT_REGEX, " ")
                _results += add_formating(r"-")
                results += _results
        return results

    def __init__(self, collection_name: str, batch_length: Optional[int] = 500) -> None:
        self.conf = Conf.get_config(collection_name, batch_length)

    def indexed(self, start: bool = True) -> None:
        if start:
            open(path.join(self.conf.storage, ".indexed"), "wb").write(b"")
            return
        with contextlib.suppress(FileNotFoundError):
            remove(path.join(self.conf.storage, ".indexed"))

    def db_prepared(self, start: bool = True) -> None:
        if start:
            open(path.join(self.conf.storage, ".dbprepared"), "wb").write(b"")
            return
        with contextlib.suppress(FileNotFoundError):
            remove(path.join(self.conf.storage, ".dbprepared"))

    def partial_indexed(self, start: bool = True) -> None:
        if start:
            open(path.join(self.conf.storage, ".part.indexed"), "wb").write(b"")
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
