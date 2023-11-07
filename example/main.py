import hashlib
import json
import urllib.parse
import urllib.request

from pykosinus import Content
from pykosinus.lib.scoring import TextScoring

req = urllib.request.Request(
    "https://gist.githubusercontent.com/ruriazz/90492766f536d807de69bff1097e1edd/raw/a0ddac05cbaafff947d1e38d316bd359b305c90d/ps2-games.txt"
)
response = urllib.request.urlopen(req)
ps2_games = response.read().decode("utf-8").split(";")

contents = [
    Content(
        identifier=hashlib.md5(word.encode("utf-8")).hexdigest(),
        content=word,
        section="game-title",
    )
    for word in ps2_games
]

similarity = (
    TextScoring(collection_name="ps2-games")
    .push_contents(contents=contents)
    .initialize()
)

while True:
    if keyword := input("keyword for search ps2-games: "):
        results = similarity.search(keyword=keyword, threshold=0.4)
        print(json.dumps([i.model_dump() for i in results], indent=3))
