import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="lab_static", static_url_path="/static")


# In-memory rate limit per IP: N requests per window_seconds
@dataclass
class RateLimit:
	limit: int
	window_seconds: int
	state: Dict[str, Tuple[int, float]]

	def allow(self, key: str) -> Tuple[bool, Optional[int]]:
		now = time.time()
		count, window_start = self.state.get(key, (0, now))
		if now - window_start > self.window_seconds:
			count = 0
			window_start = now
		count += 1
		self.state[key] = (count, window_start)
		if count > self.limit:
			retry_after = max(1, int(self.window_seconds - (now - window_start)))
			return False, retry_after
		return True, None


rate_limiter = RateLimit(limit=5, window_seconds=10, state={})


# Demo data
MOCK_POSTS = [
	{"id": "t1", "title": "Tech A", "subreddit": "technology"},
	{"id": "t2", "title": "Tech B", "subreddit": "technology"},
	{"id": "t3", "title": "Tech C", "subreddit": "technology"},
	{"id": "t4", "title": "Tech D", "subreddit": "technology"},
	{"id": "t5", "title": "Tech E", "subreddit": "technology"},
]


# Very simple token: token = HMAC-lite of (user_agent + secret) with toy algorithm.
# This is intentionally weak/educational. Secret is server-side only.
SECRET = "lab-secret-key"


def _toy_hash(s: str) -> str:
	acc = 0
	for ch in s:
		acc = ((acc << 5) - acc) + ord(ch)
		acc &= 0xFFFFFFFF
	return f"{acc:x}"


def _issue_token(user_agent: str) -> str:
	return _toy_hash(user_agent + ":" + SECRET)


@app.route("/")
def index() -> "flask.Response":
	return send_from_directory(app.static_folder, "index.html")


@app.route("/api/token", methods=["POST"])
def api_token():
	# Bind token to UA to simulate pinning to client fingerprint
	user_agent = request.headers.get("User-Agent", "")
	ok, retry_after = rate_limiter.allow(request.remote_addr or "")
	if not ok:
		resp = jsonify({"error": "rate_limited"})
		resp.status_code = 429
		resp.headers["Retry-After"] = str(retry_after)
		return resp
	return jsonify({"token": _issue_token(user_agent)})


@app.route("/api/posts", methods=["GET"])
def api_posts():
	ok, retry_after = rate_limiter.allow(request.remote_addr or "")
	if not ok:
		resp = jsonify({"error": "rate_limited"})
		resp.status_code = 429
		resp.headers["Retry-After"] = str(retry_after)
		return resp

	auth = request.headers.get("Authorization", "")
	user_agent = request.headers.get("User-Agent", "")
	expected = _issue_token(user_agent)
	if not auth.startswith("Bearer "):
		return jsonify({"error": "missing_token"}), 401
	token = auth.split(" ", 1)[1]
	if token != expected:
		return jsonify({"error": "invalid_token"}), 403

	subreddit = request.args.get("subreddit", "technology")
	limit = max(1, min(100, int(request.args.get("limit", "25"))))
	filtered = [p for p in MOCK_POSTS if p["subreddit"] == subreddit][:limit]
	return jsonify({"data": {"children": [{"data": p} for p in filtered]}})


if __name__ == "__main__":
	app.run(host="127.0.0.1", port=5000, debug=True)
