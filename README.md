# Algolia-arXiv

## Introduction

This is a toy example to experiment with the Algolia framework.

The different steps are:

- Download the latest arXiv papers
- Retrieve their number of twitter mentions
- Save it to disk
- Create an Algolia index with it
- Serve it in a simple UI/UX interface

## Set up your credentials

First, make sure to update your credentials.

```sh
$ cp twitter_credentials.json.template twitter_credentials.json
$ vim twitter_credentials.json
...
$ cp algolia_credentials.json.template algolia_credentials.json
$ vim algolia_credentials.json
...
```

## Build the index

Create the `database.json` file.

```sh
$ pipenv install
$ pipenv run python toolbox.py build_database --twitter_credentials twitter_credentials.json --database_json database.json --arxiv_count 500
$ pipenv run python toolbox.py create_algolia_index --algolia_credentials algolia_credentials.json --database_json database.json
```

## Run the front-end

```sh
$ vue ui
```
