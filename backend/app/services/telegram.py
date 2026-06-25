"""Helper minimal pour Telegram Bot API — sendMessage uniquement.

Le polling entrant (gestion des commandes praticien) est fait par un container
séparé (amana-sae-bot, cf. /bot/bot.py).
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org"


def send(chat_id: str | int, text: str, parse_mode: str = "Markdown") -> bool:
    """Envoie un message sur un chat Telegram. Retourne True si OK, False sinon.

    Dégrade silencieusement si TELEGRAM_BOT_TOKEN n'est pas configuré (utile en dev local).
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id:
        logger.info("[telegram] skipped (no token or no chat_id): %s", text[:60])
        return False
    try:
        r = requests.post(
            f"{_API_BASE}/bot{token}/sendMessage",
            json={"chat_id": str(chat_id), "text": text, "parse_mode": parse_mode},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.warning("[telegram] send failed: %s", e)
        return False
