# -*- coding: utf-8 -*-
import logging
import requests
from bs4 import BeautifulSoup
from odoo import models, fields, api, fields

_logger = logging.getLogger(__name__)

def clean_html_input(text):
    soup = BeautifulSoup(text or "", "html.parser")
    return soup.get_text(separator=" ", strip=True)

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    emotion = fields.Selection([
        ('happy', '😊 Happy'),
        ('angry', '😠 Angry'),
        ('frustrated', '😤 Frustrated'),
        ('sad', '😢 Sad'),
        ('neutral', '😐 Neutral')
    ], string='Customer Emotion')

    emotion_display = fields.Char(string='Initial Customer Emotion', compute='_compute_emotion_display', store=True)
    summary = fields.Text(string="Ticket Summary", readonly=True)
    ultimate_emotion = fields.Char(string="Ultimate Customer Emotion", readonly=True)

    @api.depends('emotion')
    def _compute_emotion_display(self):
        mapping = {
            'happy': '😊 Happy',
            'angry': '😠 Angry',
            'frustrated': '😤 Frustrated',
            'sad': '😢 Sad',
            'neutral': '😐 Neutral'
        }
        for rec in self:
            rec.emotion_display = mapping.get(rec.emotion or '', '')

    @api.model_create_multi
    def create(self, vals_list):
        records = super(HelpdeskTicket, self).create(vals_list)
        for record in records:
            if record.name or record.description:
                combined_text = clean_html_input(record.name) + " " + clean_html_input(record.description)
                _logger.info("📤 Sending cleaned text to FastAPI: %s", combined_text)
                emotion, summary = record._get_analysis_from_fastapi(combined_text)
                updates = {}
                if emotion:
                    updates['emotion'] = emotion
                if summary:
                    updates['summary'] = summary
                if updates:
                    record.write(updates)
        return records

    def action_get_analysis_from_fastapi(self):
        for record in self:
            message = clean_html_input(record.name) + " " + clean_html_input(record.description)
            _logger.info("📤 Sending cleaned text to FastAPI: %s", message)
            emotion, summary = self._get_analysis_from_fastapi(message)
            updates = {}
            if emotion:
                updates['emotion'] = emotion
            if summary:
                updates['summary'] = summary
            if updates:
                record.write(updates)

    def _get_analysis_from_fastapi(self, text):
        try:
            url = "https://mooddesk.sufalamtech.com/analyze"
            response = requests.post(url, json={"text": text}, timeout=10)
            _logger.info("📥 Received response [%s]: %s", response.status_code, response.text)
            if response.status_code == 200:
                result = response.json()
                return result.get('emotion', 'neutral'), result.get('summary', '')
            _logger.warning("FastAPI analyze error: %s %s", response.status_code, response.text)
            return 'neutral', ''
        except Exception as e:
            _logger.warning("Request error: %s", e)
            _logger.error("❌ Error occurred while calling FastAPI: %s", e)
            return 'neutral', ''
