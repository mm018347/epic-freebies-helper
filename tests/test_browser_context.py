import asyncio

import pytest
from camoufox.exceptions import UnknownProperty

import services.browser_context as browser_context
from services.browser_context import _install_hsw_identity_route


def test_hsw_route_forces_identity_without_dropping_request_headers():
    class Request:
        @staticmethod
        async def all_headers():
            return {"accept-encoding": "gzip, deflate", "x-request-id": "kept"}

    class Route:
        request = Request()
        continued_headers = None

        async def continue_(self, *, headers):
            self.continued_headers = headers

    class Context:
        pattern = None
        handler = None

        async def route(self, pattern, handler):
            self.pattern = pattern
            self.handler = handler

    async def scenario():
        context = Context()
        route = Route()
        await _install_hsw_identity_route(context)
        await context.handler(route)
        return context, route

    context, route = asyncio.run(scenario())

    assert context.pattern == "**/hsw.js*"
    assert route.continued_headers == {"accept-encoding": "identity", "x-request-id": "kept"}


@pytest.mark.parametrize(
    ("backend", "error", "fallback"),
    [
        ("auto", UnknownProperty("Unknown property navigator.appCodeName in config"), True),
        ("camoufox", UnknownProperty("Unknown property navigator.appCodeName in config"), False),
        ("auto", RuntimeError("unrelated failure"), False),
    ],
)
def test_bootstrap_schema_mismatch_fallback_is_scoped(monkeypatch, backend, error, fallback):
    import camoufox

    events = []

    class BrokenCamoufox:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            raise error

        async def __aexit__(self, *args):
            events.append("camoufox-cleaned")

    class Context:
        async def route(self, pattern, handler):
            pass

        async def close(self):
            events.append("closed")

    context = Context()

    class Playwright:
        firefox = None

        async def __aenter__(self):
            self.firefox = self
            return self

        async def __aexit__(self, *args):
            pass

        async def launch_persistent_context(self, **kwargs):
            events.append("fallback")
            return context

    monkeypatch.setattr(camoufox, "AsyncCamoufox", BrokenCamoufox)
    monkeypatch.setattr(browser_context, "async_playwright", Playwright)
    monkeypatch.setattr(browser_context, "install_playwright_frame_guard", lambda: None)
    monkeypatch.setattr(browser_context, "_camoufox_launch_options", lambda *args: {})
    monkeypatch.setattr(browser_context, "_playwright_launch_options", lambda *args, **kw: {})
    monkeypatch.setattr(browser_context.settings, "BROWSER_BACKEND", backend)
    monkeypatch.setattr(browser_context.settings, "BROWSER_PROXY", None)

    async def scenario():
        async with browser_context.open_browser_context(headless=True) as actual:
            assert actual is context
            events.append("yielded")

    if fallback:
        asyncio.run(scenario())
        assert events == ["camoufox-cleaned", "fallback", "yielded", "closed"]
    else:
        with pytest.raises(type(error), match=str(error)):
            asyncio.run(scenario())
        assert events == ["camoufox-cleaned"]
