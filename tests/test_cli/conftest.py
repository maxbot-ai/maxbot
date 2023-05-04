import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def botfile(tmp_path):
    rv = tmp_path / "bot.yaml"
    rv.write_text(
        f"""
        channels:
            viber:
                api_token: 5f3fgc4de017e5af-8ea46569dc6b60d8-adf125afb5cfd2d1
    """
    )
    return rv


@pytest.fixture
def telegram_botfile(tmp_path):
    rv = tmp_path / "bot.yaml"
    rv.write_text(
        f"""
        channels:
            telegram:
                api_token: 110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
    """
    )
    return rv
