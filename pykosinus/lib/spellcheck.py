import time
from typing import List

from spellchecker import SpellChecker

from pykosinus import log
from pykosinus.lib import BaseScoring


class SpellCheck(BaseScoring):
    _instance: SpellChecker

    def __init__(self, collection_name: str) -> None:
        super().__init__(collection_name)

        self._instance = SpellChecker(language="", distance=1)

    def correction(self, sentence: str) -> str:
        st = time.time()
        try:
            return self._get_correction_string(st, sentence)
        except TypeError:
            pass
        except Exception as err:
            log.warning(f"SpellCheck.correction was canceled due to an error: {err}")

        return sentence

    def _get_correction_string(self, st, sentence) -> str:
        corrected_string = sentence
        if words := self.get_exists_dictionary():
            self._instance.word_frequency.load_words(words)
            log.debug(
                f"SpellCheck dictionary load finish in {round(time.time() - st, 3)} seconds."
            )
            corrected_sentence = []
            for word in sentence.split():
                corrected_word = self._instance.correction(word)
                corrected_sentence.append(corrected_word)
            corrected_string = " ".join(corrected_sentence)
            if corrected_string != sentence:
                log.info(
                    f"SpellCheck.correction succeeded in correcting sentence from '{sentence}' to '{corrected_string}'"
                )
        return corrected_string

    def create_dictionary(self, dictionary: List[str], update: bool = False) -> None:
        st = time.time()
        dictionaries = []
        for word in dictionary:
            dictionaries += [i.strip() for i in word.split() if i.strip()]

        if update:
            if not self.is_filling():
                return log.warning("SpellCheck.create_dictionary cancel for updating.")
            exists_dictionaries = self.get_exists_dictionary(True, 10)
            dictionaries += [
                i.decode() for i in exists_dictionaries if isinstance(i, bytes)
            ]

        log.debug(f"total SpellCheck dictionary {len(dictionaries)} words.")
        log.debug(
            f"SpellCheck dictionary processing finish in {round(time.time() - st, 3)} seconds."
        )

        st = time.time()
        self.filling()
        self.conf.redis_client.set(
            self.conf.spell_dictionary_redis_key, " ".join(dictionaries)
        )
        self.filling(True)
        log.debug(
            f"save SpellCheck dictionary finished in {round(time.time() - st, 3)} seconds."
        )

    def get_exists_dictionary(self, waiting: bool = False, retry: int = 5) -> List[str]:
        if (
            not self.conf.redis_client.get(self.conf.spell_dictionary_redis_key)
            and waiting
            and retry > 0
        ):
            time.sleep(1)
            return self.get_exists_dictionary(waiting, retry - 1)
        elif (
            waiting
            and retry <= 0
            and not self.conf.redis_client.get(self.conf.spell_dictionary_redis_key)
        ):
            log.warning(
                "SpellCheck.get_exists_dictionary was not executed because it waited too long."
            )

        try:
            if data := self.conf.redis_client.get(self.conf.spell_dictionary_redis_key):
                return data.split()
            raise Exception(
                "SpellCheck.get_exists_dictionary failed to get master data."
            )
        except Exception:
            log.warning(
                "SpellCheck.get_exists_dictionary an error occurred because it failed to load the dictionary file."
            )
            return []

    def filling(self, end: bool = False) -> None:
        if end:
            self.conf.redis_client.delete(
                f"{self.conf.collection_config_key}.filling.spellchecker"
            )
            return
        self.conf.redis_client.set(
            f"{self.conf.collection_config_key}.filling.spellchecker",
            ":filling spell:",
            ex=300,
        )

    def is_filling(self, retry: int = 100) -> bool:
        while (
            _ := self.conf.redis_client.get(
                f"{self.conf.collection_config_key}.filling.spellchecker"
            )
            and retry > 0
        ):
            log.info("SpellCheck.create_index wait process to run ..")
            retry -= 1
            time.sleep(1.5)
        if retry == 0:
            log.warning(
                "SpellCheck.create_index was not executed because it waited too long."
            )
            return False
        return True
