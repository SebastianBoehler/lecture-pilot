# Independent LecturePilot accounts

Accounts use a verified `uni-tuebingen.de` address (including subdomains) and a
separate LecturePilot password, at least 12 characters. Never use a ZDV password.
The API does not accept the old university username/password login payload and
never creates an Alma or ILIAS session.

## Configuration

Configure these values in the ignored deployment environment:

```dotenv
LECTUREPILOT_PUBLIC_URL=https://lecturepilot.example.org
LECTUREPILOT_SMTP_HOST=smtp.example.org
LECTUREPILOT_SMTP_PORT=587
LECTUREPILOT_SMTP_FROM=LecturePilot <noreply@example.org>
LECTUREPILOT_SMTP_USERNAME=
LECTUREPILOT_SMTP_PASSWORD=
```

SMTP requires STARTTLS with certificate verification. Supply the SMTP account's
username and password when the relay requires authentication. Compose sets the
public URL from `LECTUREPILOT_DOMAIN`. Missing configuration or delivery failure
returns an actionable 503; there is no development token or console-email path.

For Tübingen deployment, the documented submission endpoint is
`smtpserv.uni-tuebingen.de:587` with STARTTLS. Obtain an approved service account
or relay; do not configure a personal student password. Leave sender and
credentials empty until the account and allowed sender have been issued.
The [ZDV application page](https://uni-tuebingen.de/en/einrichtungen/zentrum-fuer-datenverarbeitung/oft-gefragt/antraege/antraege-mit-deckblatt/)
lists the Funktions-Login-ID/E-Mail-Adresse process with a cover sheet. Confirm
whether a restricted sending relay is more suitable for automated account mail.

Registration sends a single-use verification link. Opening the link displays a
confirmation button; only submitting it creates the credential. Password reset
sends a separate single-use link and requires a new password. Links expire after
30 minutes. The database stores token hashes and scrypt password hashes, never
plaintext tokens or passwords. Expired challenges are removed on subsequent
challenge requests. Password hashing has two bounded worker slots.

## Migration and course access

Run `alembic -c apps/api/alembic.ini upgrade head` with the intended database.
Migration `20261015_0012` creates account tables and revokes all old sessions.
Back up the database before deployment.

Existing users register with their existing university email. After verification,
an exact, unambiguous email match reuses their user ID, role, private workspace,
and saved enrollments. A disabled account cannot be reclaimed. Ambiguous email
matches need operator review; the API does not guess or merge accounts.
Users without a matching email get a new student account. There is no automatic
Alma/ILIAS enrollment sync. Lecturers enable the existing join link to admit new
students to private courses.

New accounts cannot select professor or administrator privileges. After email
verification, an operator can grant a role using the existing CLI:

```bash
lecturepilot-bootstrap-admin --subject teacher@uni-tuebingen.de --role professor
lecturepilot-bootstrap-admin --subject operator@uni-tuebingen.de --role tenant_admin
```

Legacy professor roles remain attached to their original identity; operator grants
can assign an explicit LecturePilot professor role to any verified account. Role grants
are audited and revoke existing sessions. Password reset atomically replaces the
hash and revokes every session for that account. Cookie expiry, CSRF, tenant and
course checks remain in force.

## Verification boundary

Use `test_local_accounts.py` for registration, verification, cookie sessions,
reset, expiry and rejected credential payloads. SMTP tests verify mandatory TLS
and errors; an actual delivery check requires a configured relay and mailbox.
Do not describe a local test run as production deployment or email delivery.
