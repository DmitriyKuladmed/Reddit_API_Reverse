import time
import base64
import requests

from typing import Dict, Generator, Optional


class RedditApiError(Exception):
	pass


class RedditApiClient:
	"""
	Minimal OAuth2 client for Reddit's official API.
	Supports application-only auth (client credentials) and subreddit post listing.
	"""

	TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
	API_BASE_URL = "https://oauth.reddit.com"

	def __init__(
		self,
		client_id: str,
		client_secret: str,
		user_agent: str,
		request_timeout_seconds: float = 30.0,
	) -> None:
		self.client_id = client_id
		self.client_secret = client_secret
		self.user_agent = user_agent
		self.request_timeout_seconds = request_timeout_seconds

		self._access_token: Optional[str] = None
		self._access_token_expires_at_epoch: float = 0.0

	def _ensure_access_token(self) -> None:
		now = time.time()
		if self._access_token and now < self._access_token_expires_at_epoch - 30:
			return

		basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
		headers = {
			"Authorization": f"Basic {basic}",
			"User-Agent": self.user_agent,
		}
		data = {"grant_type": "client_credentials"}
		resp = requests.post(
			self.TOKEN_URL,
			headers=headers,
			data=data,
			timeout=self.request_timeout_seconds,
		)
		if resp.status_code != 200:
			raise RedditApiError(f"Token request failed: {resp.status_code} {resp.text}")
		payload = resp.json()
		self._access_token = payload.get("access_token")
		expires_in = payload.get("expires_in", 3600)
		self._access_token_expires_at_epoch = time.time() + float(expires_in)
		if not self._access_token:
			raise RedditApiError("No access_token in OAuth response")

	def _auth_headers(self) -> Dict[str, str]:
		self._ensure_access_token()
		assert self._access_token is not None
		return {
			"Authorization": f"Bearer {self._access_token}",
			"User-Agent": self.user_agent,
		}

	def _request_with_ratelimit_retry(
		self,
		method: str,
		url: str,
		params: Optional[Dict[str, str]] = None,
		max_retries: int = 5,
		initial_backoff_seconds: float = 2.0,
	) -> requests.Response:
		"""
		Respect 429 + Retry-After. Exponential backoff with bounded retries and minimal jitter.
		"""
		attempt = 0
		backoff = initial_backoff_seconds
		while True:
			resp = requests.request(
				method=method,
				url=url,
				headers=self._auth_headers(),
				params=params,
				timeout=self.request_timeout_seconds,
			)
			if resp.status_code == 429:
				attempt += 1
				if attempt > max_retries:
					raise RedditApiError("Rate limit exceeded and retries exhausted")
				retry_after = resp.headers.get("Retry-After")
				try:
					sleep_for = float(retry_after) if retry_after is not None else backoff
				except ValueError:
					sleep_for = backoff
				sleep_for = max(1.0, sleep_for)
				time.sleep(sleep_for)
				backoff = min(backoff * 2.0, 60.0)
				continue
			if 200 <= resp.status_code < 300:
				return resp
			raise RedditApiError(f"HTTP error {resp.status_code}: {resp.text}")

	def list_subreddit_posts(
		self,
		subreddit: str,
		listing: str = "new",
		limit: int = 100,
		max_items: int = 200,
		t: Optional[str] = None,
	) -> Generator[Dict, None, None]:
		"""
		Iterate posts from a subreddit listing, respecting pagination via `after`.
		- listing: one of {hot,new,top}
		- limit: page size (<=100)
		- max_items: hard bound to stop after N posts
		- t: time filter for "top" (hour, day, week, month, year, all)
		"""
		assert listing in {"hot", "new", "top"}
		fetched = 0
		after: Optional[str] = None
		while fetched < max_items:
			params: Dict[str, str] = {"limit": str(min(limit, 100))}
			if after:
				params["after"] = after
			if listing == "top" and t:
				params["t"] = t
			url = f"{self.API_BASE_URL}/r/{subreddit}/{listing}"
			resp = self._request_with_ratelimit_retry("GET", url, params=params)
			data = resp.json()
			children = data.get("data", {}).get("children", [])
			if not children:
				return
			for child in children:
				yield child.get("data", {})
				fetched += 1
				if fetched >= max_items:
					return
			after = data.get("data", {}).get("after")
			if not after:
				return
