## Calendly

When a new event gets created via Calendly, create a **Lead** in ERPNext and add a comment with more information. If the **Lead** has already been converted, the comment will be added to the corresponding **Customer** instead.

> **Note:** Currently this app can only receive webhook calls. It doesn't create the actual webhook so it's pretty useless by itself. Don't install it unless you want to contribute to the development.

### Calendly Settings

Enabled: enable or disable the calendly integration
Webhook Signing Key: Secret key from Calendly used for signing the Webhooks.

#### License

GPLv3