"""Integration with ngrok."""
import logging
from urllib.parse import urljoin, urlparse

import click

logger = logging.getLogger(__name__)


def ask_ngrok(ngrok_url):
    """Get the public url and listen address from ngrok.

    :param str ngrok_url: An URL to connect to the running ngrok application.
    :return tuple[str, str]: Listen address and public url.
    """
    import httpx  # this is too heavy to import at load time

    try:
        resp = httpx.get(urljoin(ngrok_url, "/api/tunnels"), timeout=3)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.debug(f"An error while accessing ngrok: {exc}")
        logger.error(
            f"Could not access ngrok api using {ngrok_url}.\n"
            "If ngrock is not installed go to https://ngrok.com/download and install it.\n"
            "To start a tunnel open new terminal tab and run 'ngrok http 8080'."
        )
        raise click.Abort()
    try:
        https = [t for t in resp.json().get("tunnels") if t["proto"] == "https"]
        if https:
            parsed = urlparse(https[0]["config"]["addr"])
            host, port = parsed.hostname, parsed.port
            public_url = https[0]["public_url"]
        else:
            host, port, public_url = None, None, None
    except Exception as exc:
        logger.debug(f"An error while parsing ngrok response: {exc}")
        logger.error(
            "Oops, something wrong with ngrok response.\n"
            f"Make sure you are using a valid ngrok url {ngrok_url}."
        )
        raise click.Abort()

    if host and port and public_url:
        logger.info(
            f"Obtained configuration from ngrok, forwarding {public_url} -> http://{host}:{port}."
        )
        return host, port, public_url
    logger.error(
        "Connected to ngrok, but couldn't get HTTPS configuration.\n"
        "Make sure you are started a tunnel listening for HTTPS traffic."
    )
    raise click.Abort()
