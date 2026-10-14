"""Explicit visitor registration with a durable, at-most-once CRM submission receipt."""
import asyncio
import hashlib
import json
import os
import re
import sqlite3
import secrets
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, field_validator
from . import config, registration_api

class Visitor(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=2,max_length=75)
    email:str=Field(min_length=5,max_length=254)
    phone:str=Field(min_length=8,max_length=20)
    company:str=Field(default='',max_length=120)
    @field_validator('name','company','email','phone',mode='before')
    @classmethod
    def trimmed(cls,value):return value.strip() if isinstance(value,str) else value
    @field_validator('email')
    @classmethod
    def email_format(cls,value):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):raise ValueError('Enter a valid email')
        return value
    @field_validator('phone')
    @classmethod
    def phone_format(cls,value):
        value=re.sub(r'[\s()-]','',value)
        if not re.fullmatch(r'\+[1-9]\d{6,14}',value):raise ValueError('Include + and the country code')
        return value

def remember_details(s,visitor):
    """The initial form is the visitor's identity, not permission for sales contact."""
    previous=getattr(s,'registration_profile',None)
    if previous and all(previous.get(k)==v for k,v in visitor.model_dump().items()):return
    if previous:
        s.messages[:]=[m for m in s.messages if m.get('id')!=previous.get('message_id')]
    message_id=secrets.token_urlsafe(12)
    text=f'My registration details: name {visitor.name}; email {visitor.email}; phone {visitor.phone}.'
    s.messages.append({'id':message_id,'role':'user','text':text,'kind':'customer_registration'})
    s.registration_profile={**visitor.model_dump(),'message_id':message_id}
    s.discovery_answers['contact']=True
    s.fact_evidence['contact']={'message_id':message_id,'quote':text}
    s.customer_revision+=1

def receipt(key, status=None, record_id=None, claim=False):
    path=Path(os.getenv('BEACON_REGISTRATION_DB',config.ROOT/'.state/visitor-leads.sqlite3'))
    path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path,timeout=10) as db:
        db.execute('CREATE TABLE IF NOT EXISTS receipts (key TEXT PRIMARY KEY,status TEXT,record_id TEXT)')
        if claim:
            reclaimed=db.execute("UPDATE receipts SET status='preparing' WHERE key=? AND status='not_submitted'",(key,)).rowcount
            if reclaimed:return {'status':'claimed','record_id':None}
            inserted=db.execute('INSERT OR IGNORE INTO receipts VALUES (?, ?, NULL)',(key,'preparing')).rowcount
            if inserted:return {'status':'claimed','record_id':None}
        if status:db.execute('UPDATE receipts SET status=?,record_id=? WHERE key=?',(status,record_id,key))
        row=db.execute('SELECT status,record_id FROM receipts WHERE key=?',(key,)).fetchone()
        return {'status':row[0],'record_id':row[1]} if row else None

async def register(s,visitor):
    try:
        destination=registration_api.target()
    except registration_api.RegistrationRejected as exc:
        s.registration_status='failed';s.registration_error=str(exc)
        return
    # Destination and phone scope prevent demo receipts or email changes from suppressing/duplicating capture.
    key=hashlib.sha256(('api-v1|'+destination.base+'|'+destination.tenant+'|'+visitor.phone).encode()).hexdigest()
    existing=await asyncio.to_thread(receipt,key,claim=True)
    if existing['status']!='claimed':
        s.registration_status='created' if existing['status']=='created' else 'review_required'
        if s.registration_status=='created':
            remember_details(s,visitor)
            s.registration_error=None
        else:
            s.registration_blocked_phones.add(visitor.phone)
            s.registration_error='We couldn’t confirm the registration for this number. Use a different number, or contact support for help.'
        return
    submitted=False
    try:
        destination=await registration_api.authenticate(destination)
        try:
            data=await registration_api.prepare(destination,visitor)
        except registration_api.RegistrationRejected as exc:
            if exc.code!='authentication' or not destination.username:raise
            # Read-only preflight can be repeated after sign-in. Never replay Add Lead.
            destination=await registration_api.authenticate(destination,force=True)
            data=await registration_api.prepare(destination,visitor)
        # Receipt is committed before POST. A restart or lost response cannot repeat it.
        await asyncio.to_thread(receipt,key,'submitted')
        submitted=True
        record_id=await registration_api.create(destination,data)
        await asyncio.to_thread(receipt,key,'created',record_id)
        s.registration_status='created';s.registration_error=None
        remember_details(s,visitor)
    except asyncio.CancelledError:
        if not submitted:await asyncio.to_thread(receipt,key,'not_submitted')
        else:s.registration_blocked_phones.add(visitor.phone)
        s.registration_status='review_required' if submitted else 'failed'
        raise
    except registration_api.RegistrationRejected as exc:
        if exc.code=='authentication':registration_api.invalidate(destination)
        await asyncio.to_thread(receipt,key,'not_submitted')
        s.registration_status='duplicate' if exc.code=='duplicate' else 'failed'
        s.registration_error=str(exc)
    except Exception as exc:
        await asyncio.to_thread(receipt,key,'unverified' if submitted else 'not_submitted')
        s.registration_status='review_required' if submitted else 'failed'
        if submitted:s.registration_blocked_phones.add(visitor.phone)
        s.registration_error=('We couldn’t confirm the registration for this number. Use a different number, or contact support for help.'
                      if submitted else 'We couldn’t save your details. Please try again.')
