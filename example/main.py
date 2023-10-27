import json

from pykosinus import Content
from pykosinus.lib.scoring import CosineSimilarity

contents = [
    Content(
        content="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        identifier="blog-1",
        section="blog_title",
    ),
    Content(
        content="Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        identifier="blog-2",
        section="blog_title",
    ),
    Content(
        content="Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
        identifier="blog-3",
        section="blog_title",
    ),
    Content(
        content="Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore.",
        identifier="blog-4",
        section="blog_title",
    ),
    Content(
        content="Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
        identifier="blog-5",
        section="blog_title",
    ),
    Content(
        content="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        identifier="blog-6",
        section="blog_title",
    ),
    Content(
        content="Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        identifier="blog-7",
        section="blog_title",
    ),
    Content(
        content="Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
        identifier="blog-8",
        section="blog_title",
    ),
    Content(
        content="Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore.",
        identifier="blog-9",
        section="blog_title",
    ),
    Content(
        content="Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
        identifier="blog-10",
        section="blog_title",
    ),
]

similarity = (
    CosineSimilarity(collection_name="example")
    .with_contents(contents=contents)
    .initialize()
)

while True:
    if keyword := input("keyword: "):
        results = similarity.search(keyword=keyword, threshold=0.2)
        print(json.dumps([i.dict() for i in results], indent=3))
