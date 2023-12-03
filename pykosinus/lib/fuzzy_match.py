import contextlib
import pickle
import time
from copy import deepcopy
from os import path, remove
from typing import List, Optional

from fuzzywuzzy import fuzz

from pykosinus import Content, ScoringContent, log
from pykosinus.lib import BaseScoring


class FuzzyMatch(BaseScoring):
    def search(self, keyword: str, threshold: float = 0.5) -> List[ScoringContent]:
        results = []
        st = time.time()
        if keyword := keyword.lower().replace(" ", ""):
            if indexs := self.get_index():
                for index in indexs:
                    sim = float(fuzz.ratio(keyword, index.content) / 100) - 0.05
                    if sim >= threshold:
                        index.score = sim
                        results.append(index)

        log.info(
            f"got {len(results)} FuzzyMatch similar contents with keyword '{keyword}' in {round(time.time() - st, 3)} seconds."
        )
        return sorted(results, key=lambda obj: obj.score, reverse=True)

    def create_index(self, contents: List[Content], update: bool = False) -> None:
        st = time.time()
        scoring_content = self.compile_content(contents)

        if update:
            if not self.is_filling():
                return log.warning("FuzzyMatch.create_index cancel for updating.")

            if not (indexs := self.get_index(True, 10)):
                return log.warning("FuzzyMatch.create_index cancel for updating.")

            for content in deepcopy(scoring_content):
                if content not in indexs:
                    indexs.append(content)
            scoring_content = indexs

        log.debug(f"total FuzzyMatch scoring content {len(scoring_content)}")
        log.debug(
            f"generate FuzzyMatch model finish in {round(time.time() - st, 3)} seconds."
        )

        st = time.time()
        if not self.is_filling():
            return

        self.filling()
        with open(self.conf.pickle_index_location, "wb") as f:
            pickle.dump(scoring_content, f)
        self.filling(True)
        log.debug(
            f"save FuzzyMatch model finished in {round(time.time() - st, 3)} seconds."
        )

    def get_index(
        self, waiting: bool = False, retry: int = 5
    ) -> Optional[List[ScoringContent]]:
        result: Optional[List[ScoringContent]] = None
        with contextlib.suppress(FileNotFoundError, pickle.UnpicklingError):
            with open(self.conf.pickle_index_location, "rb") as file:
                result = pickle.load(file)

        if not result and waiting and retry > 0:
            time.sleep(1)
            return self.get_index(waiting, retry - 1)
        if retry <= 0 and not result:
            log.warning(
                "FuzzyMatch.get_index was not executed because it waited too long."
            )
        return result

    def compile_content(self, contents: List[Content]) -> List[ScoringContent]:
        return super().compile_content(contents, False)

    def filling(self, end: bool = False) -> None:
        if end:
            with contextlib.suppress(FileNotFoundError):
                remove(path.join(self.conf.storage, ":filling fuzz:"))
            return
        open(path.join(self.conf.storage, ":filling fuzz:"), "wb").write(b"")

    def is_filling(self, retry: int = 100) -> bool:
        while (
            _ := path.exists(path.join(self.conf.storage, ":filling fuzz:"))
            and retry > 0
        ):
            log.info("FuzzyMatch.create_index wait process to run ..")
            retry -= 1
            time.sleep(1.5)
        if retry == 0:
            log.warning(
                "FuzzyMatch.create_index was not executed because it waited too long."
            )
            return False
        return True
