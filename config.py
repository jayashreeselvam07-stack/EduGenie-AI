import os
from pathlib import Path
from dotenv import load_dotenv

# Absolute path to root directory .env file
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

class Config:
    @classmethod
    def _reload_env(cls):
        """Reload .env file to ensure fresh configuration."""
        if ENV_PATH.exists():
            load_dotenv(dotenv_path=ENV_PATH, override=True)

    @property
    def GEMINI_API_KEY(self) -> str:
        self._reload_env()
        return os.getenv("GEMINI_API_KEY", "").strip()

    @property
    def GEMINI_MODEL(self) -> str:
        self._reload_env()
        # Default to supported current model gemini-3.8-flash
        return os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

    @property
    def HOST(self) -> str:
        return os.getenv("HOST", "127.0.0.1").strip()

    @property
    def PORT(self) -> int:
        try:
            return int(os.getenv("PORT", "8000"))
        except ValueError:
            return 8000

    MAX_INPUT_LENGTH: int = 12000  # Character limit for user input

    def is_gemini_configured(self) -> bool:
        """Check if GEMINI_API_KEY is present and not a dummy placeholder."""
        key = self.GEMINI_API_KEY
        if not key or key == "your_gemini_api_key_here" or "your_" in key.lower():
            return False
        return True

    def get_key_mask(self) -> str:
        """Return safe key status string without revealing full key."""
        key = self.GEMINI_API_KEY
        if not self.is_gemini_configured():
            return "Not Configured"
        if len(key) <= 8:
            return "Configured (Short Key)"
        return f"Configured ({key[:4]}...{key[-4:]})"

config = Config()
