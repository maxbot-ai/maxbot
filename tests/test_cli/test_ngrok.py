import logging
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from sanic import Sanic

import maxbot.cli
from maxbot import MaxBot


def test_ngrok(runner, monkeypatch, respx_mock, botfile):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())

    respx_mock.get("http://localhost:4040/api/tunnels").respond(
        json={
            "tunnels": [
                {
                    "proto": "http",
                    "public_url": "http://7ad1-109-172-248-9.ngrok.io",
                    "config": {"addr": "http://localhost:8080"},
                },
                {
                    "proto": "https",
                    "public_url": "https://7ad1-109-172-248-9.ngrok.io",
                    "config": {"addr": "http://localhost:8080"},
                },
            ]
        }
    )

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "--ngrok",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    ca = MaxBot.run_webapp.call_args
    assert ca.args == ("localhost", 8080)
    assert ca.kwargs["public_url"] == "https://7ad1-109-172-248-9.ngrok.io"

    request = respx_mock.calls.last.request
    assert request.url.path == "/api/tunnels"


def test_url(runner, monkeypatch, respx_mock, botfile):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())

    respx_mock.get("http://localhost:4041/api/tunnels").respond(
        json={
            "tunnels": [
                {
                    "proto": "http",
                    "public_url": "http://7ad1-109-172-248-9.ngrok.io",
                    "config": {"addr": "http://localhost:8080"},
                },
                {
                    "proto": "https",
                    "public_url": "https://7ad1-109-172-248-9.ngrok.io",
                    "config": {"addr": "http://localhost:8080"},
                },
            ]
        }
    )

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile, "--ngrok-url", "http://localhost:4041/"],
        catch_exceptions=False,
    )

    request = respx_mock.calls.last.request
    assert request.url.path == "/api/tunnels"


def test_option_conflict(runner, botfile):
    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile, "--ngrok", "--host", "localhost"],
        catch_exceptions=False,
    )
    assert result.exit_code == 2, result.output
    assert "Option '--ngrok'/'--ngrok-url' conflicts with '--host'." in result.output


def test_request_error(runner, respx_mock, botfile, caplog):
    respx_mock.get("http://localhost:4040/api/tunnels").respond(status_code=500)
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            maxbot.cli.main,
            ["run", "--bot", botfile, "--ngrok"],
            catch_exceptions=False,
        )
    assert result.exit_code == 1, result.output
    assert "Could not access ngrok api" in caplog.text


def test_response_error(runner, respx_mock, botfile, caplog):
    respx_mock.get("http://localhost:4040/api/tunnels").respond(json={})
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            maxbot.cli.main,
            ["run", "--bot", botfile, "--ngrok"],
            catch_exceptions=False,
        )
    assert result.exit_code == 1, result.output
    assert "Oops, something wrong with ngrok response." in caplog.text


def test_missing_configuration(runner, respx_mock, botfile, caplog):
    respx_mock.get("http://localhost:4040/api/tunnels").respond(
        json={
            "tunnels": [
                {
                    "proto": "http",
                    "public_url": "http://7ad1-109-172-248-9.ngrok.io",
                    "config": {"addr": "http://localhost:8080"},
                }
            ]
        }
    )
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            maxbot.cli.main,
            ["run", "--bot", botfile, "--ngrok"],
            catch_exceptions=False,
        )
    assert result.exit_code == 1, result.output
    assert "Connected to ngrok, but couldn't get HTTPS configuration." in caplog.text
