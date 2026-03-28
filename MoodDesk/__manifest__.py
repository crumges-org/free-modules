# -*- coding: utf-8 -*-
{
    "name": "MoodDesk",
    "summary": "AI-powered sentiment analysis tool that detects customer emotions from helpdesk tickets in Odoo.",
    "version": "1.0.0",
    "category": "Helpdesk",
    'description': """
        MoodDesk brings emotional intelligence to your Odoo Helpdesk. It analyzes incoming customer tickets and messages to detect emotional tone and sentiment, positive, neutral or negative - using AI-driven natural language processing.
        This empowers your support agents to prioritize emotionally charged tickets, de-escalate frustration early and tailor their responses with empathy.
        With built-in dashboards and emotional trend reports, MoodDesk helps improve customer satisfaction, agent performance and overall support quality.
    """,
    "license": "LGPL-3",
    "author": "Sufalam Technologies",
    "website": "https://www.sufalamtech.com",
    "depends": ["helpdesk", "mail"],
    "data": [
        "views/add_helpdesk.xml",
    ],
    'images': [
         'static/description/banner.jpg',
    ],

    "external_dependencies": {
        "python": ["bs4", "requests"]
    },
    "installable": True,
    "application": True,
}
