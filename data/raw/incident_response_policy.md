# Incident Response Policy

## Section 1: Purpose
This policy defines how the organization detects, responds to, and recovers
from cybersecurity incidents. It applies to all employees, contractors, and
third parties with access to company systems.

## Section 2: Incident Classification
Incidents are classified into four severity levels:

- **Critical**: Confirmed breach of sensitive data, ransomware execution, or
  loss of control over production systems. Requires immediate escalation to
  the CISO and executive team within 30 minutes of detection.
- **High**: Active exploitation attempt with potential for data exposure, or
  compromise of a single non-production system. Escalate to the security
  team lead within 2 hours.
- **Medium**: Suspicious activity that does not indicate active compromise,
  such as repeated failed login attempts or unusual network scanning.
  Investigate within 8 business hours.
- **Low**: Policy violations or minor anomalies with no indication of
  compromise. Log and review during routine security operations.

## Section 3: Response Procedure
1. **Detection**: Any employee who observes suspicious activity must report
   it to the security team via the incident reporting channel immediately.
2. **Containment**: The on-call security engineer isolates affected systems
   from the network to prevent lateral movement, without powering down
   systems (to preserve forensic evidence).
3. **Eradication**: Remove the root cause, including malware, unauthorized
   access, or vulnerable configurations.
4. **Recovery**: Restore affected systems from known-good backups and
   validate integrity before returning them to production.
5. **Post-Incident Review**: Within 5 business days of resolution, the
   security team produces a report covering root cause, timeline, impact,
   and remediation steps taken.

## Section 4: Communication
During a Critical or High severity incident, the designated incident
commander is the single point of communication. External communication
(customers, regulators, press) must be approved by Legal and Executive
leadership before release.

## Section 5: Roles and Responsibilities
- **Incident Commander**: Coordinates the overall response and makes final
  decisions during active incidents.
- **Security Analyst**: Performs technical investigation, containment, and
  evidence collection.
- **IT Operations**: Executes system isolation, restoration, and patching.
- **Legal/Compliance**: Assesses regulatory notification obligations (e.g.,
  breach notification laws) and reviews external communications.
