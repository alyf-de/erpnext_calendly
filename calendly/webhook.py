"""Handle Webhooks sent by Calendly"""

import time
import hmac
import hashlib
import json

import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def callback():
	calendly_settings = frappe.get_single('Calendly Settings')
	if not calendly_settings.enabled:
		frappe.throw(_('Calendly integration is currently disabled. You can enable it in Calendly Settings.'))

	secret_key = calendly_settings.get_password('webhook_signing_key')
	verify_signature(secret_key)

	data = json.loads(frappe.request.data)
	add_comment_to_party(data)


def add_comment_to_party(data):
	payload = data.get('payload', {})
	email = payload.get('email', '')
	lead_name = payload.get('name', '')
	phone = ''

	text = f'<div><b>{lead_name} created a new Event via Calendly</b></div>'
	q_and_a = payload.get('questions_and_answers', [])
	for item in q_and_a:
		question = item.get('question')
		answer = item.get('answer')

		if question == 'Telefonnummer':
			phone = answer

		text += f"<div><b>{item.get('question')}</b></div>"
		text += f"<div>{item.get('answer')}</div>"
		text += '<div><br></div>'

	text += f"""<div><a href="{payload.get('cancel_url')}">Cancel</a> or """
	text += f"""<a href="{payload.get('reschedule_url')}">Reschedule</a></div>"""

	if existing_lead := frappe.get_value(
		'Lead', filters={'email_id': email}, fieldname='name'
	):
		doc = frappe.get_doc('Lead', existing_lead)
		if doc.status == 'Converted':
			existing_customer = frappe.get_value('Customer', filters={'lead_name': doc.name}, fieldname='name')
			doc = frappe.get_doc('Customer', existing_customer)
	else:
		doc = frappe.get_doc({
			'doctype': 'Lead',
			'email_id': email,
			'lead_name': lead_name,
			'phone': phone
		}).insert(ignore_permissions=True)

	doc.add_comment(text=text, comment_by='Administrator', comment_email='Administrator')


def verify_signature(secret_key: str):
	signature_header = frappe.request.headers.get('Calendly-Webhook-Signature')
	timestamp, signature = parse_signature_header(signature_header)
	expected_signature = create_signature(timestamp, frappe.request.data, secret_key)
	if expected_signature != signature:
		frappe.throw(_('Invalid signature.'))

	# Prevent replay attacks.
	# If an attacker intercepts the webhook's payload and signature, they could
	# potentially re-transmit the request. This is known as a replay attack. This
	# type of attack can be mitigated by utilizing the timestamp in the
	# Calendly-Webhook-Signature header. In the example below, we set the
	# application's tolerance zone to 3 minutes. This helps mitigate replay attacks
	# by ensuring that requests that have timestamps that are more than 3 minutes old will
	# not be considered valid.
	tolerance = 180.0 # three minutes
	if float(timestamp) < time.time() - tolerance:
		# Signature is invalid!
		# The signature's timestamp is outside of the tolerance zone defined above.
		frappe.throw(_("Invalid Signature. The signature's timestamp is outside of the tolerance zone."))


def parse_signature_header(signature_header: str):
	key_value_pairs = signature_header.split(',')
	keys_and_values = [key_value.split('=') for key_value in key_value_pairs]
	return keys_and_values[0][1], keys_and_values[1][1]


def create_signature(timestamp: str, request_body: str, secret_key: str):
	"""Compute an HMAC with the SHA256 hash function."""
	data = '.'.join([timestamp, request_body.decode('utf-8')])
	return hmac.new(secret_key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()
