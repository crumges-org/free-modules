-- disable fcm notification
UPDATE ir_config_parameter
SET value = value || '-neu'
WHERE key = 'bista_mobile_base.firebase_project_id';
