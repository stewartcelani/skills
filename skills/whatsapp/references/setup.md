# wacli setup

Use this guide to set up wacli on one machine. It contains no account details,
recipient details, or session files.

## Install

Prefer a published binary or the Homebrew package:

```bash
brew install openclaw/tap/wacli
wacli --version
```

On systems without Homebrew, download the platform-matching archive from the
[wacli releases page](https://github.com/openclaw/wacli/releases), verify it
against the release checksum, and place the binary on `PATH`. Source builds
require a supported Go toolchain, cgo, and a C compiler; see the
[official install guide](https://wacli.sh/install.html) for current commands.

Verify the binary before pairing:

```bash
wacli --version
wacli --help
```

## Pair a linked device

Run this from a real terminal:

```bash
wacli auth
```

Scan the terminal QR code from WhatsApp's **Linked Devices** screen. After a
successful pairing, wacli performs a bootstrap sync. Confirm the result with:

```bash
wacli --json auth status
wacli --json doctor --connect
```

`auth logout` removes the local linked-device session when it is no longer
needed.

## Multiple machines and accounts

Pair each machine independently. Do not copy a wacli store between machines or
allow two machines to use one store concurrently.

For distinct WhatsApp accounts on the same machine, create isolated named
stores:

```bash
wacli accounts add work
wacli accounts list
wacli --account work auth status
```

Each account has its own linked-device session, local message mirror, media,
and lock.

## Recipient lock for agents

**Strongly recommended:** before enabling an agent to send, ask the user for
the one exact recipient phone number, in E.164 format, that the agent may
contact. Use that answer to configure a machine-local owner/recipient wrapper
or broker that accepts no recipient argument and always supplies the approved
number to wacli.

Keep the number and wrapper configuration outside this installed skill and out
of source control. Routine agent sends should invoke the locked wrapper, never
raw wacli. The wrapper should preserve wacli's JSON result, require
`success: true` and `sent: true`, and reject any attempted recipient override.

This is an application-level safeguard. A process with the same privileged
access as the account that owns the wacli store can deliberately bypass a
wrapper, so run agents without direct access to that store whenever a hard
operating-system boundary is required.

## Protect the local store

wacli stores linked-device keys and locally mirrored message data on disk. The
default location is the platform state directory (normally the XDG state
location on Linux and `~/.wacli` on macOS). Treat it like a private key:

- Keep the directory owner-only; do not relax wacli's restrictive permissions.
- Use full-disk encryption on portable machines.
- Do not commit, upload, copy, or share the store.
- Do not give agents direct read access to it unless that is an explicit,
  accepted trust decision.

`wacli sync --follow` is optional. Use it only when continuous local sync is
needed; one-shot sends do not require a daemon.

## Limits and support

wacli is a third-party WhatsApp Web client, not an official Meta API. It can
need updates when WhatsApp changes the protocol. Review the current
[wacli documentation](https://wacli.sh/) and use it in accordance with
WhatsApp's applicable terms.
