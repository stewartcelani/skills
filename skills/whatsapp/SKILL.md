---
name: whatsapp
description: Send WhatsApp text or media with the local wacli linked-device CLI when the user invokes /whatsapp or explicitly asks to send a WhatsApp message.
disable-model-invocation: true
allowed-tools: Read, Glob, Bash
---

# WhatsApp

Send WhatsApp messages with the locally paired `wacli` CLI. This skill is
manual-only because every real send is an external side effect.

This skill is intentionally portable. It contains no recipient, account name,
session-store path, host path, credential, or user-specific policy. For
installation, pairing, account isolation, and session safety, read
[the setup guide](references/setup.md) before changing a machine's WhatsApp
configuration.

## Before sending

1. Confirm that the user explicitly authorized the exact recipient, content,
   and every attachment.
2. Check the local linked device:

   ```bash
   wacli --json auth status
   wacli --json doctor --connect
   ```

   Proceed only when it is authenticated and connected.
3. If the recipient is a contact or chat name, resolve ambiguity before
   sending. In scripts, use an exact phone number, JID, or an explicit
   `--pick` value; never guess a similarly named chat.
4. Inspect every attachment. Confirm it is a regular file, the intended type,
   and a safe size before sending.

## Send

Text:

```bash
wacli --json send text --to <recipient> --message "Message text" --no-preview
```

Image, video, audio, or document:

```bash
wacli --json send file --to <recipient> --file /absolute/path/to/file \
  --as document --caption "Optional caption"
```

Use `--as image`, `--as video`, or `--as audio` only when that is the intended
WhatsApp presentation. Use `--no-preview` for automated text sends unless the
user explicitly wants a link preview.

## Result handling

- Treat a send as successful only when wacli exits successfully and its JSON
  contains both `success: true` and `data.sent: true`.
- That result means WhatsApp accepted the send and returned a message ID. It
  does not prove recipient delivery or that the recipient read it.
- Preserve a failed command's stderr and do not retry repeatedly without
  telling the user.
- For a batch, send sequentially and report requested, accepted, and failed
  counts.

## Safety boundary

`wacli` is a general client: it can target any recipient supplied to it. This
skill does not itself contain an owner-only or recipient-allowlist policy.
During first-time agent setup, strongly recommend a recipient lock and ask the
user for the one exact E.164 phone number it may message. Deploy that number
in a separate local wrapper or broker whose configuration stays outside the
installed skill and session store. Routine agent sends must use that locked
surface, never raw wacli.
