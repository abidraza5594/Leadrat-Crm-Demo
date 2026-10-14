import asyncio
import json
from contextlib import asynccontextmanager

import httpx
import pytest
from app import main, registration, registration_api as api

ID = '11111111-2222-4333-8444-555555555555'


@pytest.fixture
def backend(monkeypatch):
    monkeypatch.setenv('BEACON_REGISTRATION_API_BASE', 'https://capture.example.test')
    monkeypatch.setenv('BEACON_REGISTRATION_TENANT', 'surya')
    monkeypatch.setenv('BEACON_REGISTRATION_TOKEN', 'test-surya-token')
    monkeypatch.delenv('BEACON_REGISTRATION_USERNAME', raising=False)
    monkeypatch.delenv('BEACON_REGISTRATION_PASSWORD', raising=False)
    calls = []
    def install(handler):
        async def dispatch(request):
            calls.append(request)
            assert request.headers['tenant'] == 'surya'
            assert request.headers['authorization'] == 'Bearer test-surya-token'
            assert request.url.host == 'capture.example.test'
            return handler(request)
        @asynccontextmanager
        async def client():
            async with httpx.AsyncClient(transport=httpx.MockTransport(dispatch)) as c:
                yield c
        monkeypatch.setattr(api.transport, 'client', client)
        return calls
    return install


def visitor(phone='+12025550123', email='visitor@example.invalid'):
    return registration.Visitor(name='Test Visitor', email=email, phone=phone)


class NoBrowser:
    def __getattr__(self, name):
        raise AssertionError('Registration touched demo browser: ' + name)


def session():
    return main.Session(worker=NoBrowser())


def ok(request):
    if request.url.path.endswith('/globalsettings'):
        return httpx.Response(200, json={'succeeded': True, 'data': {'countries': [{'defaultCurrency': 'EUR'}]}})
    return httpx.Response(200, json={'succeeded': True, 'data': None if request.method == 'GET' else ID})


def test_api_only_and_repeat_does_not_create_twice_even_after_email_edit(backend):
    calls = backend(ok)
    async def run():
        s = session()
        # Even failed demo initialization must not affect registration.
        s.boot = asyncio.create_task(asyncio.sleep(3600))
        try:
            await asyncio.wait_for(registration.register(s, visitor()), 2)
            assert s.registration_status == 'created'
            assert s.registration_profile['phone'] == visitor().phone
            await registration.register(session(), visitor(email='changed@example.invalid'))
        finally:
            s.boot.cancel()
            await asyncio.gather(s.boot, return_exceptions=True)
    asyncio.run(run())
    assert [r.method for r in calls] == ['GET', 'GET', 'POST']
    body = json.loads(calls[2].content)
    assert body['contactNo'] == '2025550123' and body['countryCode'] == '+1'
    assert body['enquiry']['leadSource'] == 11
    assert 'test-surya-token' not in calls[2].content.decode()


def test_duplicate_number_can_be_corrected_without_browser(backend):
    def handler(r):
        if r.url.path.endswith('/contactno') and r.url.params['contactNo'] == '2025550123':
            return httpx.Response(200, json={'succeeded': True, 'data': {'id': ID}})
        return ok(r)
    calls = backend(handler)
    async def run():
        s = session()
        await registration.register(s, visitor())
        assert s.registration_status == 'duplicate' and not s.registration_profile
        assert not s.registration_blocked_phones
        await registration.register(s, visitor('+12025550124'))
        assert s.registration_status == 'created'
    asyncio.run(run())
    assert [r.method for r in calls] == ['GET', 'GET', 'GET', 'POST']


@pytest.mark.parametrize('failure', ['timeout', 'server', 'missing_id', 'redirect', 'bad_json'])
def test_uncertain_post_never_retried_but_new_number_works(backend, failure):
    def handler(r):
        if r.method == 'GET': return ok(r)
        if json.loads(r.content)['contactNo'] == '2025550124': return ok(r)
        if failure == 'timeout': raise httpx.ReadTimeout('Response lost', request=r)
        if failure == 'server': return httpx.Response(500)
        if failure == 'redirect': return httpx.Response(307, headers={'location': 'https://other.test'})
        if failure == 'bad_json': return httpx.Response(200, text='bad')
        return httpx.Response(200, json={'succeeded': True, 'data': None})
    calls = backend(handler)
    async def run():
        s = session()
        await registration.register(s, visitor())
        assert s.registration_status == 'review_required'
        assert visitor().phone in s.registration_blocked_phones
        await registration.register(session(), visitor())
        assert len(calls) == 3
        await registration.register(s, visitor('+12025550124'))
        assert s.registration_status == 'created'
    asyncio.run(run())
    assert [r.method for r in calls] == ['GET', 'GET', 'POST', 'GET', 'GET', 'POST']


@pytest.mark.parametrize('status', [400, 401, 403, 409, 422, 429])
def test_explicit_rejection_can_retry_after_correction(backend, status):
    rejected_once = False
    def handler(r):
        nonlocal rejected_once
        if r.method == 'POST' and not rejected_once:
            rejected_once = True
            return httpx.Response(status, json={'message': 'PRIVATE INTERNAL DETAILS'})
        return ok(r)
    backend(handler)
    async def run():
        s = session()
        await registration.register(s, visitor())
        assert s.registration_status in ('failed', 'duplicate')
        assert 'PRIVATE' not in s.registration_error and not s.registration_blocked_phones
        await registration.register(s, visitor())
        assert s.registration_status == 'created'
    asyncio.run(run())


def test_missing_token_fails_without_using_demo_credentials(backend, monkeypatch):
    calls = backend(ok)
    monkeypatch.delenv('BEACON_REGISTRATION_TOKEN')
    s = session()
    asyncio.run(registration.register(s, visitor()))
    assert s.registration_status == 'failed' and not calls


def test_receipts_are_tenant_scoped(backend, monkeypatch):
    calls = backend(ok)
    asyncio.run(registration.register(session(), visitor()))
    # An old demo receipt is not a Surya registration receipt.
    import hashlib
    old = hashlib.sha256((registration.config.CRM_ORIGIN+'|'+visitor().email+'|'+visitor().phone).encode()).hexdigest()
    assert registration.receipt(old) is None
    assert len(calls) == 3


def test_international_phone_split_preserves_italian_zero():
    data = api.payload(visitor('+390236618300'))
    assert data['countryCode'] == '+39' and data['contactNo'] == '0236618300'


def test_invalid_phone_rejected_before_network(backend):
    calls = backend(ok)
    s = session()
    asyncio.run(registration.register(s, visitor('+123456789')))
    assert s.registration_status == 'failed' and not calls


def test_concurrent_submissions_share_durable_claim(backend):
    calls = backend(ok)
    async def run():
        sessions = [session(), session()]
        await asyncio.gather(*(registration.register(s, visitor()) for s in sessions))
        assert any(s.registration_status == 'created' for s in sessions)
    asyncio.run(run())
    assert sum(r.method == 'POST' for r in calls) == 1


def test_preflight_timeout_can_retry_without_write(backend):
    failed = False
    def handler(r):
        nonlocal failed
        if not failed:
            failed = True
            raise httpx.ReadTimeout('Lookup failed', request=r)
        return ok(r)
    calls = backend(handler)
    async def run():
        s = session()
        await registration.register(s, visitor())
        assert s.registration_status == 'failed' and not s.registration_blocked_phones
        await registration.register(s, visitor())
        assert s.registration_status == 'created'
    asyncio.run(run())
    assert [r.method for r in calls] == ['GET', 'GET', 'GET', 'POST']


def test_surya_empty_lookup_is_not_an_api_error(backend):
    def handler(r):
        if r.url.path.endswith('/contactno'):
            return httpx.Response(200, json={'succeeded': False, 'data': None,
                'errors': None, 'message': None, 'actionCode': None, 'isClockInMandatory': False})
        return ok(r)
    calls = backend(handler)
    s = session()
    asyncio.run(registration.register(s, visitor()))
    assert s.registration_status == 'created'
    assert json.loads(calls[-1].content)['enquiry']['currency'] == 'EUR'


def test_credentials_login_cache_and_expiry(monkeypatch):
    import base64
    import time
    def token(exp):
        return 'header.' + base64.urlsafe_b64encode(json.dumps({'exp': exp}).encode()).decode().rstrip('=') + '.signature'
    issued = token(time.time()+3600)
    calls = []
    destination = api.Target('https://capture.test', 'surya', '', 'https://identity.test', 'user', 'secret')
    api._auth_cache.clear()
    def handle(r):
        calls.append(r)
        assert r.url == 'https://identity.test/api/tokens'
        assert r.headers['tenant'] == 'surya'
        assert json.loads(r.content)['username'] == 'user'
        return httpx.Response(200, json={'succeeded': True, 'data': {'idToken': issued}})
    @asynccontextmanager
    async def client():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as c:yield c
    monkeypatch.setattr(api.transport, 'client', client)
    async def run():
        one = await api.authenticate(destination)
        assert one.token == issued and 'secret' not in repr(one) and issued not in repr(one)
        await api.authenticate(destination)
        assert len(calls) == 1
        api._auth_cache[api.auth_key(destination)] = token(time.time()-1)
        await api.authenticate(destination)
        assert len(calls) == 2
        api.invalidate(destination)
        await api.authenticate(destination)
        assert len(calls) == 3
    asyncio.run(run())


def test_read_auth_recovery_does_not_retry_create(backend, monkeypatch):
    calls = backend(ok)
    destination = api.Target('https://capture.example.test', 'surya', 'test-surya-token',
                             'https://identity.test', 'user', 'secret')
    monkeypatch.setattr(api, 'target', lambda: destination)
    auth = []
    async def authenticate(t, force=False):auth.append(force);return t
    original = api.prepare
    attempts = []
    async def prepare(t, v):
        attempts.append(1)
        if len(attempts) == 1:raise api.RegistrationRejected('Expired', 'authentication')
        return await original(t, v)
    monkeypatch.setattr(api, 'authenticate', authenticate)
    monkeypatch.setattr(api, 'prepare', prepare)
    s = session()
    asyncio.run(registration.register(s, visitor()))
    assert auth == [False, True] and s.registration_status == 'created'
    assert sum(r.method == 'POST' for r in calls) == 1
