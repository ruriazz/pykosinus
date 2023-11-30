# pykosinus

pykosinus is an open-source Python library for text similarity search scoring. It provides a fast and memory-efficient way to calculate cosine similarity scores, making it suitable for various text similarity applications. The library is designed to be user-friendly and encourages contributions from the community.

## Installation

To install pykosinus, make sure you have Python 3.8.17 or higher installed. Then, you can install the library using pip:

```shell
pip install pykosinus
```

## Additional Library for Mac Users
If you are using pykosinus on a Mac, you may need to install the GCC compiler to enable certain features. GCC is a widely used compiler for various programming languages.

To install GCC on macOS, you can use Homebrew, a popular package manager for macOS. Follow these steps to install GCC using Homebrew:

- Open a terminal window.
- Install Homebrew by running the following command:
```sh
[/bin/bash](VALID_FILE) -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
- Install GCC by running the following command:
```sh
brew install gcc
```
- Verify the installation by running the following command:
```sh
gcc --version
```
- Set gfortran
```sh
export FC=gfortran
```

- Verify gfortran installation
```sh
gfortran --version
```

- Install openblas and set pkg config openblas
```sh
brew install openblas
```
```sh
export PKG_CONFIG_PATH="/opt/homebrew/opt/openblas/lib/pkgconfig"
```


## Usage
To use pykosinus in your Python project, you can follow these steps:

- Import the necessary modules and classes:
```python
from pykosinus import Content
from pykosinus.lib.scoring import TextScoring
```

- Create an instance of the **TextScoring** class, providing the collection name as a parameter:
```python
similarity = TextScoring(collection_name)
```

- Set the contents to be searched using the **push_contents** method, passing a list of **Content** objects:
```python
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
    # Add more contents as needed
]
similarity.push_contents(contents)
```

- Initialize the similarity search by calling the **initialize** method:
```python
similarity.initialize()
```

- Perform a similarity search by calling the **search** method, providing a keyword and an optional threshold:
```python
results = similarity.search(keyword="search keyword", threshold=0.2)
```

- The **search** method returns a list of **ScoringResult** objects, which contain the relevant information about the search results. You can access the properties of each result, such as **identifier**, **content**, **section**, **similar**, and **score**.
```python
for result in results:
    print(
        result.identifier, result.content, result.section, result.similar, result.score
    )
```


## Contributing
pykosinus welcomes contributions from the community. If you would like to contribute to the library, please follow these steps:
- Fork the pykosinus repository on [**GitHub**](https://github.com/ruriazz/pykosinus).
- Create a new branch for your feature or bug fix.
- Make your changes and commit them with descriptive commit messages.
- Push your changes to your forked repository.
- Submit a pull request to the master pykosinus repository, explaining the changes you have made.

## Versioning
pykosinus is currently in version 0.1.4. We encourage continuous development and contributions from other contributors to improve and expand the library.

## License
pykosinus is released under the [MIT License](https://opensource.org/licenses/MIT).