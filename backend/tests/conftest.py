from __future__ import annotations

import pytest

from contester import create_app


@pytest.fixture()
def app():
    application = create_app("testing")
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
