# Access Control Policy

## Section 1: Purpose
This policy establishes requirements for granting, reviewing, and revoking
access to organizational systems and data, based on the principle of least
privilege.

## Section 2: Access Provisioning
- All access requests must be submitted through the access management
  system and approved by the resource owner and the requester's manager.
- Access is granted based on job role using role-based access control
  (RBAC). Standing access to production systems requires additional
  approval from the security team.
- Temporary elevated access ("just-in-time" access) expires automatically
  after 8 hours unless explicitly renewed.

## Section 3: Authentication Requirements
- Multi-factor authentication (MFA) is required for all access to systems
  handling sensitive data, remote access (VPN), and administrative accounts.
- Passwords must be a minimum of 14 characters. Password sharing between
  individuals is strictly prohibited under all circumstances.
- Service accounts must use certificate-based authentication or managed
  secrets rather than static passwords where technically feasible.

## Section 4: Access Review
- Access rights for all systems classified as sensitive or critical are
  reviewed quarterly by resource owners.
- Any access not used within 90 days is automatically flagged for
  revocation unless justified by the resource owner.
- Upon role change or termination, access must be revoked within 24 hours
  for voluntary departures and immediately for involuntary terminations.

## Section 5: Privileged Access Management
- Administrative and privileged accounts are separate from standard user
  accounts and are not used for routine tasks such as email or browsing.
- All privileged session activity is logged and retained for a minimum of
  one year.
- Break-glass emergency access procedures require post-use justification
  submitted within 24 hours and are reviewed by the security team.

## Section 6: Third-Party Access
External vendors and contractors are granted the minimum access necessary
for the duration of their engagement only, and all third-party access is
reviewed monthly by the security team.
