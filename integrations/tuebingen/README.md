# Tübingen Integration

The integration is implemented in the API through the published
`tue-api-wrapper==0.3.0` package. This directory records the integration
boundary; it contains no separate deployable package.

Current responsibilities:

- authenticate credentials and verify the server-reported active Alma role;
- return quickly after identity/role verification, then synchronize the
  lightweight Alma timetable and ILIAS memberships in the background;
- persist sync loading/error state and replace stale external enrollments;
- match a student's own upstream memberships conservatively to exact
  title-and-term platform courses; and
- keep university credentials and provider sessions out of browser and
  LecturePilot persistence.

Practice-exam enrichment uses the wrapper's `PpiClient` directly with a new,
short-lived client for each learner request. PPI has a separate password from
the university account. LecturePilot never stores either credential or the PPI
session. Existing entitlements download without a token; new borrowing requires
an explicit one-token confirmation and a fresh remote state check.

The adapter code is in `apps/api/src/lecturepilot/tuebingen_adapter.py`; account
and matching policy is documented in
[`../../docs/tenancy-security.md`](../../docs/tenancy-security.md).
