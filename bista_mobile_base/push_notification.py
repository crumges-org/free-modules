import base64
import json
import requests
import logging
import time
from datetime import datetime

try:
    from google.oauth2 import service_account
    from google.auth.transport import requests as google_requests
except ImportError:
    service_account = None

_logger = logging.getLogger(__name__)


def firebase_send_notification(self, payload_data):
    try:
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        firebase_project_id = IrConfigParameter.get_param("bista_mobile_base.firebase_project_id")
        firebase_admin_key_file = IrConfigParameter.get_param(
            "bista_mobile_base.firebase_admin_key_file"
        )

        if not firebase_project_id or not firebase_admin_key_file:
            _logger.exception("Some firebase configuration is missing from the settings.")
            return False

        if service_account:
            firebase_data = json.loads(base64.b64decode(firebase_admin_key_file).decode())
            firebase_credentials = service_account.Credentials.from_service_account_info(
                firebase_data, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
            )
            firebase_credentials.refresh(google_requests.Request())
            auth_token = firebase_credentials.token

            for notification_data in payload_data:
                start_time = time.time()
                topic = str(notification_data["topic"])
                notification_data.update({"serverUrl": IrConfigParameter.get_param("web.base.url")})
                _logger.info(f"Firebase notification start time :{datetime.now()}")
                response = requests.post(
                    f"https://fcm.googleapis.com/v1/projects/{firebase_project_id}/messages:send",
                    json={
                        "message": {
                            # "topic": f'{server_env}_topic_id_{topic}',
                            "topic": topic,
                            "notification": {
                                "title": notification_data["title"],
                                "body": notification_data["body"],
                            },
                            "data": notification_data,
                        }
                    },
                    headers={"authorization": f"Bearer {auth_token}"},
                    timeout=5,
                )
                end_time = time.time()
                # _logger.info('Firebase notification end time', datetime.now())
                _logger.info(f"Firebase notification response time in seconds {str(end_time - start_time)}")
            return True

            # print(json.loads(response.text), f'topic_id_{partner_ids[0]}' if partner_ids else "")
        else:
            _logger.exception(
                "You have to install" '"google_auth>=1.18.0" to be able to send push ' "notifications."
            )
            return False
    except Exception as e:
        _logger.exception("Error while sending notification: %s" % e)
