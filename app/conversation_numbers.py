"""Parse an entire count reply, never a number buried in a product request."""
import re
from decimal import Decimal, InvalidOperation


def count_reply(text):
    text=text.strip().lower().rstrip('.!')
    words=dict(zip('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split(),range(20)))
    words.update(dict(zip('twenty thirty forty fifty sixty seventy eighty ninety'.split(),range(20,100,10))))
    scaled=re.fullmatch(r'([a-z]+(?:[ -][a-z]+)?)\s+(thousand|lakhs?|million)',text)
    if scaled:
        base=count_reply(scaled[1])
        if base is not None:return base*{'thousand':1000,'lakh':100000,'lakhs':100000,'million':1000000}[scaled[2]]
    # Whole number phrases only; this does not rewrite arbitrary product requests.
    parts=text.replace('-',' ').split()
    if parts and all(p in words for p in parts) and len(parts)<=2:
        if len(parts)==1:return words[parts[0]]
        if words[parts[0]]>=20 and 0<words[parts[1]]<10:return words[parts[0]]+words[parts[1]]
    match=re.fullmatch(
        r'(?:(?:we get|we have|we receive|about|around|approximately|roughly)\s+)*'
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*'
        r'(k|thousand|thousands|lakh|lakhs|lac|lacs|million|m)?'
        r'(?:\s+(?:new\s+)?(?:people|agents|members|leads))?'
        r'(?:\s*(?:per month|a month|monthly|/\s*month|on our sales team))?',text)
    if not match:return None
    number,unit=match.groups()
    if ',' in number and not (re.fullmatch(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?',number)
                             or re.fullmatch(r'\d{1,2}(?:,\d{2})*,\d{3}(?:\.\d+)?',number)):
        return None
    multiplier={None:1,'k':1000,'thousand':1000,'thousands':1000,
                'lakh':100000,'lakhs':100000,'lac':100000,'lacs':100000,
                'm':1000000,'million':1000000}[unit]
    try:value=Decimal(number.replace(',',''))*multiplier
    except InvalidOperation:return None
    return int(value) if 0<=value<=1000000000 and value==value.to_integral_value() else None
