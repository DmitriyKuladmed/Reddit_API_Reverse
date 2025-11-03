from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
	reddit_client_id: str
	reddit_client_secret: str
	reddit_user_agent: str = "reddit-tech-fetcher/1.0 (contact:noreply@example.com)"

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=False,
	)
