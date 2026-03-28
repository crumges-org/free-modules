# -*- coding: utf-8 -*-
import logging
import re
import requests
from bs4 import BeautifulSoup
from odoo import models, api, fields

_logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, vals_list):
        messages = super(MailMessage, self).create(vals_list)

        for message in messages:
            try:
                # Only process incoming partner messages on helpdesk tickets (exclude internal users)
                if (
                    message.model == 'helpdesk.ticket'
                    and message.body
                    and not message.author_id.user_ids  # no related internal user -> external partner
                ):
                    ticket = self.env['helpdesk.ticket'].browse(message.res_id)
                    body_text = self._clean_html(message.body)

                    payload = {
                        "ticket_id": ticket.id,
                        "ticket_name": ticket.name,
                        "sender": message.author_id.name,
                        "message": body_text,
                        "timestamp": fields.Datetime.to_string(message.date) if message.date else '',
                    }

                    _logger.info("📤 Sending conversation to FastAPI with payload: %s", payload)
                    response = requests.post("https://mooddesk.sufalamtech.com/conversation", json=payload, timeout=5)
                    response.raise_for_status()
                    response_data = response.json()

                    emotion = response_data.get("emotion")
                    summary = response_data.get("summary")

                    _logger.info("✅ Conversation response: %s", response_data)

                    updates = {}
                    if summary:
                        updates['summary'] = summary
                    if emotion:
                        updates['ultimate_emotion'] = emotion
                    if updates:
                        ticket.write(updates)
            except Exception as e:
                _logger.error("❌ Failed to send conversation to FastAPI: %s", str(e))

        return messages

    def _clean_html(self, html):
        # Step 1: Convert HTML to plain text
        text = BeautifulSoup(html or "", "html.parser").get_text()

        # Step 2: Remove email reply history and signatures
        reply_patterns = [
            r"On.*wrote:",
            r"From:.*",
            r"Sent from my.*",
            r"^>.*$",
            r"--+\s*\n.*",
        ]
        for pattern in reply_patterns:
            text = re.split(pattern, text, flags=re.IGNORECASE | re.MULTILINE)[0]

        # Step 3: Clean up invisible characters and whitespace
        text = re.sub(r'[\u200b\u200c\u200d\uFEFF\xa0]', '', text)
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)

        return text.strip()
