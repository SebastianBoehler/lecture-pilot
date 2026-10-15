# Tübingen integration

LecturePilot does not accept ZDV credentials or create authenticated Alma/ILIAS
sessions. Accounts use verified university email and separate passwords. See
[account setup](../../docs/local-accounts.md).

The optional `tue-api-wrapper==0.3.0` package remains for public Alma course
search and PPI exam-protocol imports. Public search does not authenticate.
PPI uses its own password, independent of ZDV; its short-lived client and
credentials remain request-only. New borrowing requires explicit token-spend
confirmation. Existing imported protocols remain private to their learner.

Historical university identity and enrollment records remain for account
recovery and existing course access. No login refreshes these records.
New students join courses through lecturer-issued join links.
