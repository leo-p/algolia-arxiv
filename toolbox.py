import json
import arxiv
import twitter
import argparse
from tqdm import tqdm
from algoliasearch.search_client import SearchClient


def open_json_from_file(json_path):
    with open(json_path) as json_file:
        return json.load(json_file)


def save_json_to_file(json_data, json_path, pretty=False):
    with open(json_path, 'w') as json_file:
        if pretty:
            json.dump(json_data, json_file, indent=4, sort_keys=True)
        else:
            json.dump(json_data, json_file)


def pretty_print(inline_json):
    print(json.dumps(inline_json, indent=4, sort_keys=True))
    return


def get_latest_arxiv_articles(count):
    query_results = arxiv.query(
        query="a",
        max_results=count,
        sort_by="lastUpdatedDate",
        sort_order="descending",
        prune=True
    )

    papers = []
    for paper in tqdm(query_results):
        papers.append({
            'url': paper['arxiv_url'],
            'authors': paper['authors'],
            'category': paper['arxiv_primary_category']['term'],
            'last_update': paper['updated'],
            'title': paper['title'],
            'abstract': paper['summary']
        })
    return papers


def add_twitter_mentions_to_papers(papers, twitter_credentials, database_json, include_retweets=False):
    # Intialize the API client
    api = twitter.Api(
        consumer_key=twitter_credentials['api_key'],
        consumer_secret=twitter_credentials['api_key_secret'],
        access_token_key=twitter_credentials['access_token'],
        access_token_secret=twitter_credentials['access_token_secret'],
        sleep_on_rate_limit=True
    )

    for ii, paper in enumerate(tqdm(papers)):
        # Compute the number of tweets and retweets for both arxiv urls
        arxiv_id = paper['url'].split('http://arxiv.org/abs/')[1].split('v')[0]
        mentions = 0
        for doc in ['abs', 'pdf']:
            for tweet in api.GetSearch(term=f'arxiv.org/{doc}/{arxiv_id}', result_type='recent', count=100):
                mentions += 1
                if include_retweets:
                    mentions += len(api.GetRetweets(statusid=tweet.id_str))
        paper['twitter_mentions'] = mentions

        # Add resilience to twitter api rate limiting
        if (ii + 1) % 15 == 0:
            save_json_to_file(papers, database_json, pretty=True)

    return papers


def create_algolia_index(index_name, papers, algolia_credentials, max_objects_per_batch=1000):
    # Initialize the index
    client = SearchClient.create(algolia_credentials['app_id'], algolia_credentials['admin_key'])
    index = client.init_index(index_name)
    index.set_settings({
        'searchableAttributes': [
            'title',
            'abstract',
            'authors'
        ]
    })

    # Add objects with batching
    papers_per_batch = [papers[i:i + max_objects_per_batch] for i in range(0, len(papers), max_objects_per_batch)]
    for batch in tqdm(papers_per_batch):
        index.save_objects(batch, {'autoGenerateObjectIDIfNotExist': True})


if __name__ == '__main__':
    # Setup argparser for the sub-commands
    parser = argparse.ArgumentParser(description='Toolbox scripts.')
    subparsers = parser.add_subparsers(dest='command')

    # Create the parser for the command
    description = 'Retrieve latest arxiv articles and their twitter mentions'
    subparser = subparsers.add_parser('build_database', help=description, description=description)
    subparser.add_argument('--twitter_credentials', action='store', type=str, help='Twitter credentials JSON')
    subparser.add_argument('--arxiv_count', action='store', type=int, default=5, help='Number of arxiv articles to retrieve')
    subparser.add_argument('--database_json', action='store', type=str, help='Database JSON output')

    # Create the parser for the command
    description = 'Create and update the Algolia index'
    subparser = subparsers.add_parser('create_algolia_index', help=description, description=description)
    subparser.add_argument('--algolia_credentials', action='store', type=str, help='Algolia credentials JSON')
    subparser.add_argument('--database_json', action='store', type=str, help='Database JSON output')
    subparser.add_argument('--index_name', action='store', type=str, help='Algolia index name')

    # Parse all the arguments
    args = parser.parse_args()
    cmd = args.command

    if cmd == 'build_database':
        # Retrieve arguments
        twitter_credentials = open_json_from_file(args.twitter_credentials)
        arxiv_count = args.arxiv_count
        database_json = args.database_json

        # Retrieve arxiv articles
        papers = get_latest_arxiv_articles(arxiv_count)

        # Retrieve twitter mentions
        add_twitter_mentions_to_papers(papers, twitter_credentials, database_json)

    elif cmd == 'create_algolia_index':
        # Retrieve arguments
        algolia_credentials = open_json_from_file(args.algolia_credentials)
        papers = open_json_from_file(args.database_json)
        index_name = args.index_name

        # Initialize the algolia index
        create_algolia_index(index_name, papers, algolia_credentials)
