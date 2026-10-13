# Security

Do not publish API keys, account cookies, tokens, student data, screenshots of private question pages, or raw logs containing them. Run logs intentionally omit question text and redact common `sk-` credentials, but review an export before sharing it.

For a security issue, contact the maintainer privately through GitHub's private vulnerability reporting feature if enabled. Otherwise open an Issue containing only a non-sensitive summary and request a private contact channel. Do not put exploit steps or credentials in a public Issue.

When started, the browser script sends the visible question stem and choices directly to DeepSeek from the user's browser. Its API Key is stored by Tampermonkey; the Windows application uses Windows Credential Manager. A released key must be revoked at the provider. The project does not attempt to bypass restricted pages, captchas, desktop permissions, or platform security controls.
