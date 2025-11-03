import argparse
import json

from reddit_api_client import RedditApiClient
from settings import AppSettings


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Fetch posts from a subreddit using Reddit official API",
	)
	parser.add_argument("subreddit", type=str, help="Subreddit name, e.g., technology")
	parser.add_argument(
		"--listing",
		type=str,
		default="new",
		choices=["hot", "new", "top"],
		help="Listing type",
	)
	parser.add_argument("--max-items", type=int, default=100, help="Max posts to fetch")
	parser.add_argument("--limit", type=int, default=100, help="Page size (<=100)")
	parser.add_argument(
		"--top-window",
		type=str,
		choices=["hour", "day", "week", "month", "year", "all"],
		help="Time window for 'top' listing",
	)
	parser.add_argument(
		"--output",
		type=str,
		default="jsonl",
		choices=["jsonl", "json"],
		help="Output format",
	)
	return parser.parse_args()


def main() -> None:
	args = parse_args()

	settings = AppSettings()

	client = RedditApiClient(
		client_id=settings.reddit_client_id,
		client_secret=settings.reddit_client_secret,
		user_agent=settings.reddit_user_agent,
	)

	posts_iter = client.list_subreddit_posts(
		subreddit=args.subreddit,
		listing=args.listing,
		limit=args.limit,
		max_items=args.max_items,
		t=args.top_window,
	)

	if args.output == "jsonl":
		for post in posts_iter:
			print(json.dumps(post, ensure_ascii=False))
	else:
		all_posts = list(posts_iter)
		print(json.dumps(all_posts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
	main()
