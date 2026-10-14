"""Suggested answers to the active business question; not intent-routing rules."""

CHOICES = {
    'organisation.type': [('Developer', 'I am a developer.'), ('Brokerage', 'I run a brokerage.'),
                          ('Channel partner', 'I am a channel partner.')],
    'organisation.agents': [(str(n), f'We have {n} people on our sales team.') for n in (5, 10, 25, 50, 100, 300)],
    'monthly_leads': [(f'{n:,}', f'We receive {n} new leads per month.') for n in (100, 500, 1000, 5000, 20000, 100000)],
    'process': [('Excel', 'We use Excel to manage leads.'), ('WhatsApp', 'We use WhatsApp to manage leads.'),
                ('Another CRM', 'We currently use another CRM.'), ('Manually', 'We manage leads manually.')],
    'pain_points': [('Missed follow-ups', 'Our biggest problem is missing follow-ups.'),
                    ('Manual work', 'Our biggest problem is too much manual data entry.'),
                    ('Lead assignment', 'Our biggest problem is assigning leads to the right people.'),
                    ('Tracking the team', 'Our biggest problem is tracking our sales team’s work.')],
    'influence': [('I decide', 'I am the person deciding which CRM to buy.'),
                  ('We decide together', 'Our team and I decide on the CRM together.'),
                  ('Evaluating for someone', 'I am evaluating the CRM for someone else.')],
    'next_step': [('Now', 'We want to start using a new CRM now.'),
                  ('Within a month', 'We want a new CRM running within the next month.'),
                  ('Later', 'We want to start using a new CRM later.'),
                  ('Just exploring', 'We are just exploring and have not decided when to start.')],
    'consent': [('Yes, contact me', 'Yes, I would like the Leadrat team to contact me.'),
                ('No, thank you', 'No, I do not want to be contacted.')],
    'contact': [],
}

def for_question(question):
    if question not in CHOICES:return None
    return {'question':question,
            'options':[{'label':label,'message':message} for label,message in CHOICES[question]],
            'custom_label':'Enter another number' if question in {'organisation.agents','monthly_leads'} else 'Write my own answer',
            'skip_message':'I would prefer to skip this question for now.'}
