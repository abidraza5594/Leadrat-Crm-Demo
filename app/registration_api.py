"""Visitor capture through the tenant API, independent of the demo browser.

Contract: CRM leads.service.ts, BaseService.add and AddLead's payload/response.
Never replay a POST after an ambiguous response. The receipt is owned by registration.py.
"""
import os
import asyncio
import base64
import hashlib
import json
import time
from dataclasses import dataclass, field, replace
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx
import phonenumbers
from . import transport


class RegistrationRejected(Exception):
    def __init__(self, message, code='validation'):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Target:
    base: str
    tenant: str
    token: str = field(repr=False)
    identity: str = ''
    username: str = field(default='', repr=False)
    password: str = field(default='', repr=False)

    @property
    def endpoint(self):
        return self.base + '/api/v1/lead'

    @property
    def headers(self):
        return {'Authorization': 'Bearer ' + self.token, 'tenant': self.tenant,
                'Accept': 'application/json'}


def target():
    base = os.getenv('BEACON_REGISTRATION_API_BASE', '').strip().rstrip('/')
    tenant = os.getenv('BEACON_REGISTRATION_TENANT', '').strip()
    token = os.getenv('BEACON_REGISTRATION_TOKEN', '').strip()
    username = os.getenv('BEACON_REGISTRATION_USERNAME', '').strip()
    password = os.getenv('BEACON_REGISTRATION_PASSWORD', '')
    identity = os.getenv('BEACON_REGISTRATION_IDENTITY_BASE', '').strip().rstrip('/')
    parsed = urlsplit(base)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
            parsed.password or parsed.path or parsed.query or parsed.fragment or
            not tenant or not (token or (username and password)) or any(c in tenant + token for c in '\r\n')):
        raise RegistrationRejected('Registration is temporarily unavailable. Please try again later.', 'configuration')
    if username and password:
        url = urlsplit(identity)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.path or url.query or url.fragment:
            raise RegistrationRejected('Registration is temporarily unavailable. Please try again later.', 'configuration')
    return Target(base, tenant, token.removeprefix('Bearer '), identity, username, password)


_auth_lock = asyncio.Lock()
_auth_cache = {}
_login_id = str(uuid4())


def auth_key(destination):
    return hashlib.sha256((destination.base+'|'+destination.identity+'|'+destination.tenant+'|'+
                          destination.username+'|'+destination.password).encode()).hexdigest()


def invalidate(destination):
    _auth_cache[auth_key(destination)] = ''


def expires(token):
    # Used only for refresh scheduling; CRM verifies the actual token/signature.
    try:
        part = token.split('.')[1]
        return float(json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4)))['exp'])
    except (ValueError, KeyError, IndexError, TypeError):
        return 0


async def authenticate(destination, force=False):
    if not (destination.username and destination.password):
        return destination
    key = auth_key(destination)
    async with _auth_lock:
        token = _auth_cache.get(key, destination.token)
        if not force and expires(token) > time.time() + 60:
            return replace(destination, token=token)
        async with transport.client() as client:
            response = await client.post(destination.identity + '/api/tokens',
                headers={'tenant': destination.tenant, 'Accept': 'application/json'},
                json={'username': destination.username, 'password': destination.password,
                      'LoginId': _login_id, 'DeviceName': 'Beacon Backend', 'DeviceModel': 'Server',
                      'DeviceUDID': 'beacon-registration-backend', 'Platform': 2},
                timeout=20, follow_redirects=False)
        rejected(response)
        result = response.json()
        data = (result.get('data') or {}) if isinstance(result, dict) else {}
        token = data.get('idToken') if isinstance(data, dict) else None
        if not token or result.get('succeeded') is not True or expires(token) <= time.time() + 60:
            raise RegistrationRejected('Registration is temporarily unavailable. Please try again later.', 'authentication')
        _auth_cache[key] = token
        return replace(destination, token=token)


def payload(visitor):
    try:
        number = phonenumbers.parse(visitor.phone, None)
        if not phonenumbers.is_valid_number(number):
            raise ValueError('Invalid phone')
    except (phonenumbers.NumberParseException, ValueError):
        raise RegistrationRejected('Enter a valid phone number for the selected country.') from None
    return {'name': visitor.name, 'email': visitor.email,
            'contactNo': phonenumbers.national_significant_number(number),
            'countryCode': '+' + str(number.country_code), 'companyName': visitor.company or None,
            'notes': 'Website visitor registered for a Beacon demo.',
            'assignTo': None, 'secondaryUserId': None, 'address': {}, 'unitIds': [],
            'gender': 0, 'maritalStatus': 0, 'profession': 0, 'possesionType': 0,
            'enquiry': {'leadSource': 11, 'subSource': None, 'lowerBudget': '0', 'upperBudget': '0',
                        'bhkTypes': [], 'bhKs': [], 'beds': [], 'baths': [],
                        'enquiryTypes': [], 'propertyTypeIds': [], 'addresses': [],
                        'carpetArea': 0, 'builtUpArea': 0, 'saleableArea': 0,
                        'propertyArea': 0, 'netArea': 0}}  # CRM LeadSource.Website enum.


def rejected(response):
    # Provider response bodies can contain PII/internal errors; do not show or log them.
    if response.status_code == 409:
        raise RegistrationRejected('This phone number is already registered. Enter a different number.', 'duplicate')
    if response.status_code in (401, 403):
        raise RegistrationRejected('Registration is temporarily unavailable. Please try again later.', 'authentication')
    if response.status_code in (400, 422):
        raise RegistrationRejected('These details could not be accepted. Please check your name, email and phone number.')
    if response.status_code == 429:
        raise RegistrationRejected('Registration is busy. Please try again shortly.', 'rate_limit')
    response.raise_for_status()


async def prepare(destination, visitor):
    data = payload(visitor)
    async with transport.client() as client:
        response = await client.get(destination.endpoint + '/contactno', headers=destination.headers,
            params={'contactNo': data['contactNo'], 'countryCode': data['countryCode'],
                    'canAccessAllLeads': 'false'}, timeout=15, follow_redirects=False)
    rejected(response)
    result = response.json()
    # Surya QA returns HTTP 200, succeeded=false, data=null for no matching number.
    empty_lookup = (isinstance(result, dict) and result.get('succeeded') is False
                    and 'data' in result and result['data'] is None
                    and not result.get('message') and not result.get('errors')
                    and not result.get('actionCode') and not result.get('isClockInMandatory'))
    if not isinstance(result, dict) or (result.get('succeeded') is not True and not empty_lookup):
        raise RegistrationRejected('We couldn’t check your details. Please try again.')
    existing = result.get('data')
    if isinstance(existing, dict) and existing.get('id'):
        raise RegistrationRejected('This phone number is already registered. Enter a different number.', 'duplicate')
    if existing is not None and not isinstance(existing, dict):
        raise RegistrationRejected('We couldn’t check your details. Please try again.')
    # Use this tenant's currency, as the actual CRM form does (never assume INR).
    async with transport.client() as client:
        settings_response = await client.get(destination.base + '/api/v1/globalsettings',
            headers=destination.headers, timeout=15, follow_redirects=False)
    rejected(settings_response)
    settings = settings_response.json()
    countries = (settings.get('data') or {}).get('countries') if isinstance(settings, dict) else None
    if not countries or not countries[0].get('defaultCurrency'):
        raise RegistrationRejected('We couldn’t load registration settings. Please try again.')
    data['enquiry']['currency'] = countries[0]['defaultCurrency']
    return data


async def create(destination, data):
    # No retries and no implicit redirect: a timeout may still mean the record was saved.
    async with transport.client() as client:
        response = await client.post(destination.endpoint, headers=destination.headers,
            json=data, timeout=20, follow_redirects=False)
    rejected(response)
    result = response.json()
    if isinstance(result, dict) and result.get('succeeded') is False:
        raise RegistrationRejected('These details could not be accepted. Please check the form.')
    if not isinstance(result, dict) or result.get('succeeded') is not True:
        raise ValueError('Unconfirmed registration result')
    record_id = result.get('data')
    if not isinstance(record_id, str) or UUID(record_id).int == 0:
        raise ValueError('Missing registration record ID')
    return record_id
