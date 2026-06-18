"""
ProcessPilot AI â€” Rich Demo Data Seeder v2
Populates the system with 10+ enterprise documents across all departments,
20+ tasks in various states, 4 meetings, and realistic search scenarios.

Run after starting the server:
  cd backend
  python seed_demo.py
"""
import requests
import json
import tempfile
import os
import sys

# Reconfigure stdout to use UTF-8 to prevent UnicodeEncodeError on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api/v1"

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# RICH DOCUMENT CONTENT
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

DOCS = [
    # â”€â”€ ENGINEERING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "filename": "deployment_guide.txt",
        "dept": 1,
        "content": """FastAPI Kubernetes Deployment Guide
===================================
Engineering Department | Version 2.1 | Last Updated: June 2025

PREREQUISITES
-------------
- Docker Desktop or Docker Engine 24+
- kubectl configured for target cluster
- Access to container registry: registry.processpilot.ai
- Helm 3.12+

STEP 1: BUILD DOCKER IMAGE
--------------------------
  docker build -t processpilot-api:latest .
  docker tag processpilot-api:latest registry.processpilot.ai/api:v{VERSION}
  docker push registry.processpilot.ai/api:v{VERSION}

STEP 2: DEPLOY TO KUBERNETES
-----------------------------
  # Apply configuration
  kubectl apply -f k8s/configmap.yaml
  kubectl apply -f k8s/secrets.yaml
  kubectl apply -f k8s/deployment.yaml
  kubectl apply -f k8s/service.yaml
  kubectl apply -f k8s/ingress.yaml

  # Verify rollout
  kubectl rollout status deployment/processpilot-api
  kubectl get pods -l app=processpilot-api

STEP 3: HEALTH CHECKS
---------------------
  curl https://api.processpilot.ai/health
  curl https://api.processpilot.ai/
  # Expected: {"status": "healthy"} and {"status": "operational"}

STEP 4: ENVIRONMENT VARIABLES
------------------------------
Required in Kubernetes secrets:
  DATABASE_URL          - PostgreSQL or SQLite connection string
  SECRET_KEY            - JWT signing key (256-bit random)
  GEMINI_API_KEY        - (optional) Google AI key
  GROQ_API_KEY          - (optional) Groq API key
  CHROMA_PERSIST_DIR    - Path for ChromaDB persistence
  CORS_ORIGINS          - Comma-separated allowed origins

ROLLBACK PROCEDURE
------------------
  kubectl rollout undo deployment/processpilot-api
  kubectl rollout status deployment/processpilot-api
  # Verify with health check

COMMON ISSUES
--------------
1. "CrashLoopBackOff" â€” Check environment variables in configmap
2. "ImagePullBackOff" â€” Verify registry credentials in imagePullSecrets
3. "Connection refused" â€” Check service port mapping and ingress annotations
4. Database migration errors â€” Run: kubectl exec -it <pod> -- python -m alembic upgrade head

CONTACTS
--------
DevOps: devops@processpilot.ai | Slack: #devops-support
On-call rotation: PagerDuty â†’ Engineering Manager â†’ CTO
"""
    },
    {
        "filename": "incident_response_sop.txt",
        "dept": 1,
        "content": """Incident Response Standard Operating Procedure
================================================
Engineering Department | Version 3.0 | June 2025

PURPOSE
-------
Define a consistent, efficient process for detecting, responding to,
and recovering from system incidents.

SEVERITY LEVELS
---------------
  P1 â€” CRITICAL  : Production down, data loss risk, security breach
                   Response SLA: 15 minutes
  P2 â€” HIGH      : Major feature unavailable, significant user impact
                   Response SLA: 1 hour
  P3 â€” MEDIUM    : Feature degraded, workaround available
                   Response SLA: 4 hours
  P4 â€” LOW       : Minor bug, no immediate user impact
                   Response SLA: Next sprint

INCIDENT RESPONSE WORKFLOW
---------------------------
1. DETECTION
   - Automated alerting via PagerDuty / Datadog
   - User report via support@processpilot.ai
   - Internal monitoring dashboards

2. TRIAGE (0â€“15 min)
   - Acknowledge alert in PagerDuty
   - Post in #incidents Slack channel: "[P{N}] {brief description} â€” investigating"
   - Assign Incident Commander (IC) â€” on-call engineer
   - Identify affected systems and customer impact

3. RESPONSE (ongoing)
   - IC coordinates all communications
   - Create JIRA ticket with severity label and timeline
   - Updates every 30 min in #incidents for P1/P2
   - Implement fix or rollback as needed

4. RESOLUTION
   - Verify fix with health checks and monitoring
   - Confirm user-facing systems restored
   - Post resolution message in #incidents

5. POST-MORTEM (within 48 hours for P1/P2)
   - Schedule blameless retrospective
   - Document: timeline, root cause, contributing factors
   - Action items with owners and due dates
   - Share report with engineering leadership

ESCALATION MATRIX
------------------
  P1: Notify CTO + VP Engineering within 15 min
  P2: Notify Engineering Manager within 30 min
  P3: Notify Team Lead within 2 hours
  P4: Add to sprint backlog

KNOWN INCIDENTS LOG
--------------------
2025-03-15 â€” P2 â€” API deployment failed: Missing DATABASE_URL in Kubernetes
             configmap. Fixed by updating deployment manifest.
2025-04-02 â€” P1 â€” ChromaDB corruption after OOM kill. Fixed: increased
             memory limits to 4Gi, added persistence volume.
2025-05-20 â€” P3 â€” Auth tokens expiring too early. Fixed: JWT expiry
             extended from 30min to 8 hours.

CONTACTS
--------
Incident channel: #incidents (Slack)
On-call calendar: PagerDuty (Engineering rotation)
Post-mortem template: Confluence â†’ Engineering â†’ Templates
"""
    },
    {
        "filename": "code_review_standards.txt",
        "dept": 1,
        "content": """Code Review Standards & Process
================================
Engineering Department | Version 1.4

PURPOSE
-------
Ensure code quality, knowledge sharing, and consistent style across
all ProcessPilot AI repositories.

REVIEW CHECKLIST
----------------
All PRs must pass the following before merge:

[ ] Functionality
    - Does the code do what the ticket requires?
    - Edge cases handled?
    - No obvious logic errors

[ ] Code Quality
    - Follows PEP8 (Python) / ESLint config (JavaScript)
    - Functions < 50 lines, files < 300 lines
    - No magic numbers â€” use named constants
    - No commented-out dead code

[ ] Security
    - No secrets or API keys in code
    - Input validation on all user-provided data
    - SQL queries use parameterized inputs (no raw string concatenation)
    - Auth checks on all protected endpoints

[ ] Performance
    - No N+1 queries â€” use eager loading
    - Appropriate indexes on new DB columns
    - No blocking calls in async handlers

[ ] Tests
    - Unit tests for new business logic
    - Integration tests for new API endpoints
    - Coverage must not decrease from baseline (80%)

[ ] Documentation
    - Docstrings on all public functions
    - README updated if new setup steps required
    - API schema updated for new/changed endpoints

PR PROCESS
----------
1. Create branch from main: feature/PP-{ticket}-description
2. Self-review the diff before requesting review
3. Request 2 reviewers (1 senior + 1 peer)
4. Respond to all comments within 24 hours
5. Squash commits before merge
6. Delete branch after merge

PR SIZE GUIDELINES
------------------
Ideal: < 200 lines changed
Max: 400 lines (exceptions require lead approval)
For large changes: break into stacked PRs

REVIEW TURNAROUND
-----------------
- First review: within 24 hours of assignment
- Reviewer resolves unaddressed comments before approving
- IC/lead reviews PRs touching critical paths (auth, payments)

LINTING & FORMATTING
---------------------
Backend (Python): black, isort, flake8 (configured in pyproject.toml)
Frontend (JS/React): ESLint + Prettier (run: npm run lint)
Pre-commit hooks: enabled via .pre-commit-config.yaml

CONTACTS
--------
Code quality: engineering-lead@processpilot.ai | #code-review (Slack)
"""
    },
    {
        "filename": "security_policy.txt",
        "dept": 1,
        "content": """Information Security Policy
============================
Engineering & Operations | Version 2.0 | June 2025

SCOPE
-----
All employees, contractors, and systems processing company or customer data.

ACCESS CONTROL
--------------
1. Principle of Least Privilege
   - Users granted minimum access required for their role
   - Access reviewed quarterly by department heads
   - Privileged access (admin/prod) requires MFA

2. Password Policy
   - Minimum 12 characters, uppercase + lowercase + number + symbol
   - Changed every 90 days for privileged accounts
   - No password reuse (last 12 passwords)
   - Use 1Password for credential management

3. API Keys & Secrets
   - Never commit secrets to version control
   - Store in AWS Secrets Manager or Kubernetes secrets
   - Rotate API keys every 180 days
   - Revoke immediately upon employee offboarding

DATA CLASSIFICATION
--------------------
  RESTRICTED  â€” Customer PII, financial data, authentication credentials
                Encryption: AES-256 at rest, TLS 1.3 in transit
  INTERNAL    â€” Business processes, internal docs, analytics
                Access: Employees only
  PUBLIC      â€” Marketing materials, public documentation
                No restrictions

GDPR & DATA PRIVACY
--------------------
- Data retention: 3 years for business records, 1 year for logs
- Customer data deletion: processed within 30 days of request
- Data breach notification: ICO + affected users within 72 hours
- DPA (Data Processing Agreement) required for all vendors

SECURITY INCIDENT REPORTING
-----------------------------
- Report immediately to: security@processpilot.ai
- Do NOT attempt to fix or investigate independently
- Preserve evidence â€” do not delete logs or files
- Suspected phishing: forward to security team, do not click links

PENETRATION TESTING
-------------------
- Annual external pentest by certified firm
- Internal vulnerability scans: monthly (automated)
- Bug bounty program: security.processpilot.ai/bug-bounty

ACCEPTABLE USE
--------------
- Company systems for business purposes only
- No installation of unauthorized software
- Personal devices accessing company data must be enrolled in MDM
- VPN required for accessing internal services remotely

CONTACTS
--------
CISO: security@processpilot.ai
Emergency (breach): +1-800-PILOT-SEC
"""
    },

    # â”€â”€ HR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "filename": "onboarding_checklist.txt",
        "dept": 2,
        "content": """New Employee Onboarding Checklist
===================================
HR Department | Updated: June 2025

BEFORE DAY 1 (HR & IT Action Items)
-------------------------------------
[ ] Send welcome email with first-day instructions
[ ] Provision company laptop (standard config via IT)
[ ] Create email account: firstname.lastname@processpilot.ai
[ ] Set up Slack, Jira, GitHub, and Confluence access
[ ] Order access card and office parking permit
[ ] Schedule Day 1 orientation with HR
[ ] Assign onboarding buddy from same department

WEEK 1 â€” ORIENTATION
----------------------
Day 1:
[ ] Office tour and introductions
[ ] Meet HR: paperwork, benefits enrollment, company handbook
[ ] IT setup: laptop, email, tools, VPN, MFA
[ ] Meet team lead, receive welcome + overview of role
[ ] Access ProcessPilot AI (internal tool) â€” watch tutorial video

Day 2-3:
[ ] Complete compliance training: Security Awareness (2h)
[ ] Complete HR training: Code of Conduct, Anti-harassment (1h)
[ ] Complete GDPR & Data Privacy training (45 min)
[ ] Review department SOPs and knowledge base

Day 4-5:
[ ] Shadow senior team member
[ ] First 1-on-1 with direct manager
[ ] Set 30/60/90 day goals with manager

WEEK 2 â€” INTEGRATION
---------------------
[ ] Attend first sprint planning / team meeting
[ ] Complete development environment setup (Engineering only)
[ ] Begin contributing to low-complexity tickets
[ ] Attend department all-hands

WEEK 3-4 â€” CONTRIBUTION
------------------------
[ ] First independent PR / deliverable submitted
[ ] Complete remaining optional trainings
[ ] Submit onboarding feedback survey (link from HR)
[ ] Schedule first performance check-in (30-day review)

90-DAY MILESTONE REVIEW
------------------------
[ ] Formal 90-day performance review with manager
[ ] Confirm probation period outcome (where applicable)
[ ] Update goals for next quarter
[ ] Explore any additional access/tooling needs

CONTACTS
--------
HR: hr@processpilot.ai | Slack: #people-ops
IT Helpdesk: it@processpilot.ai | Slack: #it-support
"""
    },
    {
        "filename": "leave_policy.txt",
        "dept": 2,
        "content": """Leave & Time Off Policy
=========================
HR Department | Effective: January 2025

ANNUAL LEAVE (PTO)
------------------
- Full-time employees: 20 days per year
- Accrual: 1.67 days per month from start date
- Unused PTO: max 5 days carry-forward to next year
- PTO payout on resignation: yes (accrued and unused)

REQUEST PROCESS
---------------
1. Submit leave request in HR portal minimum:
   - 1 day notice for 1-2 days
   - 1 week notice for 3-5 days
   - 3 weeks notice for 1+ week
2. Manager approval required within 48 hours
3. Update shared team calendar
4. Set OOO email auto-reply
5. Handover document for absences > 3 days

SICK LEAVE
----------
- Entitlement: 10 days per year (non-accruing, not carried forward)
- Medical certificate required for 3+ consecutive sick days
- Extended illness (> 2 weeks): covered by company insurance policy

PUBLIC HOLIDAYS
---------------
India office: 10 national/regional holidays (see HR portal)
US office: Federal holidays + Good Friday, Day after Thanksgiving
All holidays published in company calendar at start of year

PARENTAL LEAVE
--------------
- Primary caregiver: 26 weeks paid maternity/paternity leave
- Secondary caregiver: 4 weeks paid leave
- Adoption: same as primary caregiver leave
- Coverage: 100% of base salary for first 16 weeks

UNPAID LEAVE
------------
- Up to 4 weeks per year with manager + HR approval
- Longer sabbaticals: evaluated case by case

EMERGENCY / BEREAVEMENT LEAVE
-------------------------------
- Death of immediate family member: 5 days paid
- Death of extended family: 2 days paid
- Emergency (family illness, natural disaster): case by case

CONTACTS
--------
HR Portal: hr.processpilot.ai
HR team: hr@processpilot.ai | Slack: #people-ops
Leave queries: leave@processpilot.ai
"""
    },
    {
        "filename": "performance_review_sop.txt",
        "dept": 2,
        "content": """Employee Performance Review Process
=====================================
HR Department | Version 1.2 | June 2025

REVIEW CYCLE
------------
- Continuous feedback: ongoing (encouraged weekly 1:1s)
- Mid-year check-in: June (informal, no formal rating)
- Annual review: December (formal rating + compensation discussion)
- Probation review: 90 days from start date

RATING SCALE
------------
  5 â€” Exceptional     : Consistently exceeds all expectations
  4 â€” Exceeds         : Regularly exceeds expectations
  3 â€” Meets           : Consistently meets expectations
  2 â€” Developing      : Partially meets expectations, needs improvement
  1 â€” Unsatisfactory  : Does not meet expectations

REVIEW PROCESS TIMELINE
------------------------
Week 1 (Dec 1-7):
  - HR sends review forms to all employees
  - Employees complete self-assessment

Week 2 (Dec 8-14):
  - Managers complete performance ratings
  - Peer feedback collected (360 optional)
  - Calibration meeting: all managers with HR

Week 3 (Dec 15-21):
  - Manager-employee review conversation
  - Goals set for next year
  - Compensation adjustments finalized

Week 4 (Dec 22+):
  - Reviews locked in system
  - Comp changes effective Jan 1

SELF-ASSESSMENT TEMPLATE
-------------------------
1. Key accomplishments this year (3-5 bullet points)
2. Progress on prior year goals
3. Skills developed or certifications earned
4. Areas for improvement (be honest)
5. Goals for next year (SMART format)
6. Career development aspirations

MANAGER RESPONSIBILITIES
-------------------------
- Complete reviews on time (HR tracks)
- Provide specific, evidence-based feedback (not vague)
- No surprises â€” address issues in real-time via 1:1s
- Document all performance conversations in HR system
- Create PIP (Performance Improvement Plan) for rating â‰¤ 2

COMPENSATION GUIDELINES (Confidential)
----------------------------------------
  Rating 5: 8-12% salary increase + full bonus
  Rating 4: 5-8% salary increase + full bonus
  Rating 3: 2-5% salary increase + partial bonus
  Rating 2: 0-2% increase, no bonus, PIP required
  Rating 1: No increase, probation, may result in separation

CONTACTS
--------
HR Business Partner: hrbp@processpilot.ai
Performance system: hr.processpilot.ai/reviews
Questions: Slack #people-ops
"""
    },

    # â”€â”€ OPERATIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "filename": "disaster_recovery_plan.txt",
        "dept": 3,
        "content": """Business Continuity & Disaster Recovery Plan
=============================================
Operations Department | Version 2.5 | June 2025

OBJECTIVES
----------
- RTO (Recovery Time Objective): 4 hours for critical systems
- RPO (Recovery Point Objective): 1 hour (last backup point)
- Availability target: 99.9% uptime

CRITICAL SYSTEMS (Priority Order)
-----------------------------------
1. Authentication service (JWT / database)
2. API backend (FastAPI + ChromaDB)
3. Frontend (Vite build)
4. Document storage
5. Analytics database

BACKUP STRATEGY
---------------
Database (SQLite/PostgreSQL):
  - Automated nightly backups to S3
  - Point-in-time recovery enabled
  - Backup retention: 30 days
  - Test restores: monthly

ChromaDB Vector Store:
  - Snapshot every 6 hours to persistent volume
  - Full backup to S3 nightly
  - Recovery: restore from snapshot, re-index if needed

Document Files:
  - Uploaded files mirrored to S3 bucket
  - Versioning enabled on S3
  - Retention: indefinite

DISASTER SCENARIOS & PLAYBOOKS
--------------------------------
1. DATABASE CORRUPTION
   - Stop application pods
   - Restore from last clean backup
   - Validate data integrity
   - Restart and run smoke tests

2. SERVER / VM FAILURE
   - Kubernetes auto-restarts failed pods
   - If node failure: drain node, reschedule pods
   - If cluster failure: restore from Terraform state

3. DATA CENTER OUTAGE
   - Traffic fails over to secondary region (AWS ap-southeast-1)
   - DNS TTL: 60 seconds (fast failover)
   - Estimated recovery: 30-60 minutes

4. SECURITY BREACH / RANSOMWARE
   - Immediately isolate affected systems (network quarantine)
   - Notify CISO and legal
   - Restore from pre-breach backup
   - Conduct forensics before bringing systems online
   - Notify affected users per GDPR requirements

DR TESTING SCHEDULE
-------------------
- Monthly: Backup restore validation
- Quarterly: Full DR drill (simulated outage)
- Annually: Third-party DR audit

COMMUNICATION PLAN
------------------
Internal: Incident Slack channel + email to all@processpilot.ai
Customer: Status page (status.processpilot.ai) updated within 15 min
Media inquiries: PR team only (pr@processpilot.ai)

CONTACTS
--------
Operations Lead: ops@processpilot.ai
DR Coordinator: dr@processpilot.ai
AWS Support: Enterprise support plan active
"""
    },
    {
        "filename": "vendor_management_sop.txt",
        "dept": 3,
        "content": """Vendor Selection & Management Process
=======================================
Operations Department | Version 1.3

PURPOSE
-------
Ensure consistent, risk-conscious evaluation and management of
all third-party vendors providing services or products to ProcessPilot AI.

VENDOR CATEGORIES
-----------------
  Tier 1: Critical vendors (access to production data or systems)
           Examples: AWS, Datadog, PagerDuty
  Tier 2: Significant vendors (access to non-production systems)
           Examples: Slack, Jira, GitHub
  Tier 3: Standard vendors (no system access)
           Examples: Office supplies, training platforms

VENDOR SELECTION PROCESS
--------------------------
1. REQUIREMENTS GATHERING
   - Define use case, budget, and technical requirements
   - Identify security and compliance requirements
   - Get sign-off from department head

2. MARKET EVALUATION
   - Evaluate minimum 3 vendors
   - Complete Vendor Evaluation Matrix (Confluence template)
   - Check G2/Gartner reviews and references

3. SECURITY REVIEW (Tier 1 & 2)
   - Request vendor SOC2 Type II report
   - Complete security questionnaire
   - Review data processing practices + GDPR compliance
   - Approval from IT/Security team required

4. NEGOTIATION & CONTRACTING
   - Legal review of all contracts
   - Ensure DPA (Data Processing Agreement) in place for data vendors
   - Standard payment terms: Net 30
   - SLA and penalty clauses for critical vendors

5. ONBOARDING
   - Document vendor in vendor registry (IT portal)
   - Configure SSO if available
   - Brief relevant team members

ONGOING VENDOR MANAGEMENT
---------------------------
- Annual security review for Tier 1 vendors
- Quarterly performance review for critical vendors
- Monitor for vendor financial health and news
- Contract renewals: 90-day advance notice to budget owner

OFFBOARDING VENDORS
-------------------
- Revoke all access within 24 hours of termination
- Request data deletion confirmation
- Archive contract and service records (7 years)

APPROVED VENDOR LIST
--------------------
Cloud: AWS (primary), GCP (secondary)
Monitoring: Datadog
Alerting: PagerDuty
Comms: Slack, Zoom
HRIS: BambooHR
Finance: QuickBooks

CONTACTS
--------
Procurement: procurement@processpilot.ai
Legal (contracts): legal@processpilot.ai
IT Security (review): security@processpilot.ai
"""
    },

    # â”€â”€ FINANCE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "filename": "budget_planning_guide.txt",
        "dept": 4,
        "content": """Annual Budget Planning Guide
=============================
Finance Department | FY 2026 Planning Cycle

PLANNING TIMELINE
-----------------
September:   Finance sends budget templates to all department heads
October:     Department heads submit draft budgets
November:    Finance consolidation, CFO review
December:    Board approval
January:     Final budgets communicated to departments

BUDGET CATEGORIES
-----------------
Personnel (typically 65-70% of total budget):
  - Salaries and wages
  - Benefits (25% of salary loaded cost)
  - Contractor / consultant fees
  - Recruitment fees (15% of placed salary)

Technology & Infrastructure (typically 15-20%):
  - Cloud infrastructure (AWS)
  - SaaS tools and subscriptions
  - Hardware / equipment
  - Licenses

Operations (10-15%):
  - Office rent and utilities
  - Travel and accommodation
  - Training and development
  - Marketing and events

HEADCOUNT PLANNING
------------------
All new hires must be in approved headcount plan BEFORE:
  1. Job requisition is opened
  2. Offer letter is extended
Exceptions: emergency replacements for departures (same level/cost)

BUDGET SUBMISSION REQUIREMENTS
--------------------------------
Each department must submit:
1. Prior year actuals vs. budget variance (explain > 10% variances)
2. Current year forecast (Q3 + Q4 estimates)
3. Next year budget request with justification
4. Headcount plan: existing + planned new hires
5. CapEx requests (> $5,000 single items)
6. Key assumptions used in projections

APPROVAL THRESHOLDS
--------------------
  Up to $5,000      : Department head approval
  $5,001 - $25,000  : Department head + CFO approval
  $25,001 - $100,000: CFO + CEO approval
  > $100,000        : Board approval required

COST CENTER CODES
-----------------
  ENG-001: Engineering (General)
  ENG-002: Engineering (Infrastructure / Cloud)
  HR-001:  HR & Recruiting
  OPS-001: Operations
  FIN-001: Finance
  MKT-001: Marketing

EXPENSE REIMBURSEMENT
----------------------
- Submit within 30 days of expense
- All expenses > $100 require receipt
- Travel: pre-approval required for flights > $500
- Client entertainment: documented with attendees list
- Reimburse via: payroll (monthly) or Expensify direct

CONTACTS
--------
Finance: finance@processpilot.ai
CFO: cfo@processpilot.ai
Budget queries: Slack #finance-help
Expense reimbursement: expense@processpilot.ai
""",
    },
    {
        "filename": "data_privacy_policy.txt",
        "dept": 4,
        "content": """Data Privacy & GDPR Compliance Policy
=======================================
Legal / Finance / Operations | Version 2.1 | June 2025

SCOPE
-----
Applies to all personal data collected, processed, or stored by ProcessPilot AI
and its employees, including customer data, employee data, and vendor data.

DATA WE COLLECT
---------------
Customer Data:
  - Account information (email, name, role)
  - Usage data (queries, documents uploaded, interactions)
  - Technical data (IP address, browser, device)
  - Billing information (handled by payment processor)

Employee Data:
  - Contact and identity information
  - Payroll and tax records
  - Performance and HR records

HOW WE USE DATA
---------------
- Provide and improve our services
- Authentication and access control
- Usage analytics (anonymized where possible)
- Legal and regulatory compliance
- Customer support and communication

LAWFUL BASIS FOR PROCESSING (GDPR Article 6)
----------------------------------------------
  Customer data: Contract performance + Legitimate interest
  Employee data: Legal obligation + Contract
  Marketing: Consent (explicit opt-in only)

DATA RETENTION
--------------
  Account data:        Duration of account + 3 years post-deletion
  Usage/audit logs:    1 year rolling retention
  Financial records:   7 years (legal requirement)
  HR records:          7 years post-employment
  Support tickets:     3 years after resolution

DATA SUBJECT RIGHTS (GDPR)
---------------------------
Customers may exercise these rights via: privacy@processpilot.ai
  Right of Access       â€” Receive copy of personal data (30-day SLA)
  Right to Rectification â€” Correct inaccurate data (30-day SLA)
  Right to Erasure      â€” Delete data (30-day SLA, unless legal hold)
  Right to Portability  â€” Receive data in machine-readable format
  Right to Object       â€” Object to certain processing

DATA BREACH PROTOCOL
--------------------
1. Detect and contain breach
2. Assess scope (data types, number of subjects)
3. Notify CISO and Legal within 1 hour
4. Notify ICO within 72 hours (if GDPR scope)
5. Notify affected individuals if high risk
6. Document incident and corrective actions

THIRD-PARTY DATA SHARING
--------------------------
Data shared only with:
  - Subprocessors with signed DPA (see vendor registry)
  - Law enforcement with valid legal order (notify customer unless prohibited)
  - No data sold or shared for advertising

EMPLOYEE PRIVACY
----------------
Company monitoring limited to:
  - Access logs for security investigation
  - Email on company systems (disclosed in employment contract)
  - Never: personal messages, GPS tracking without consent

CONTACTS
--------
Data Protection Officer: dpo@processpilot.ai
Privacy requests: privacy@processpilot.ai
ICO registration number: ZA000000
""",
    },
]

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TASKS (20+)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

TASKS = [
    # Pending
    ("Update Docker Compose Config", "Add new environment variables for Groq and Gemini API integration"),
    ("Write API Documentation", "Document all REST endpoints using OpenAPI spec in Confluence"),
    ("Set Up Datadog Alerts", "Configure alerting for P1/P2 threshold breaches on production APIs"),
    ("GDPR Data Audit Q3", "Audit all data stores for GDPR compliance. Check retention policies."),
    ("Update Leave Policy Page", "Add parental leave clarifications approved in last board meeting"),
    ("Vendor Security Review â€” Datadog", "Annual SOC2 review for Datadog monitoring platform"),
    ("Create 2026 Budget Templates", "Send budget planning templates to all department heads by Sep 1"),
    ("Refresh Onboarding Videos", "Re-record onboarding tutorial videos for new ProcessPilot UI"),

    # In Progress
    ("Set Up CI/CD Pipeline", "Configure GitHub Actions for automated testing, linting, and deployment"),
    ("AWS Infrastructure Migration", "Migrate legacy EC2 instances to EKS. 60% complete."),
    ("Security Awareness Training", "Roll out Q3 security awareness module to all 47 employees"),
    ("DR Plan Q3 Drill", "Conduct quarterly disaster recovery drill â€” test database restore from S3"),
    ("Performance Review System Setup", "Configure BambooHR for December annual review cycle"),

    # Completed
    ("Database Migration Script", "Alembic migration for new analytics tables â€” completed and deployed"),
    ("Setup ChromaDB Persistence", "Configured persistent volume for ChromaDB vector store on Kubernetes"),
    ("Fix JWT Expiry Bug", "Extended token expiry from 30min to 8 hours to improve UX"),
    ("Q2 Budget Report", "Prepared Q2 actuals vs. budget variance report for CFO review"),
    ("Onboarding Buddy Program", "Launched buddy program pairing new hires with senior team members"),
    ("SSO Integration â€” Slack", "Completed SAML 2.0 SSO integration for Slack workspace"),
    ("Security Penetration Test", "Annual external pentest completed. 2 medium findings remediated."),
    ("Update CORS Configuration", "Added production domain to CORS allowed origins in FastAPI config"),
    ("Employee Handbook 2025", "Updated handbook with new leave policy and hybrid work guidelines"),
]

STATUS_MAP = {i: "Pending" for i in range(8)}
STATUS_MAP.update({i: "In_Progress" for i in range(8, 13)})
STATUS_MAP.update({i: "Completed" for i in range(13, len(TASKS))})

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MEETINGS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

MEETINGS = [
    {
        "title": "Q3 Infrastructure Planning",
        "transcript": """CTO: Good morning everyone. Let's start with the infrastructure migration status.

Engineering Lead (Rohan): We're at 60% on the AWS migration. The main blocker right now is finalizing the database migration strategy â€” we need to decide between Aurora PostgreSQL and RDS.

DevOps Lead (Sarah): I recommend Aurora for the connection pooling benefits. I've prepared a cost comparison. Aurora would run about $340/month versus $280 for standard RDS, but the scalability and failover story is much better.

CTO: Let's go with Aurora. Finance, does that fit in Q3 budget?

Finance Lead (Mark): Yes, I've already factored in a $400 buffer for infra upgrades in Q3.

CTO: Good. Sarah, when can you have the DR runbook finalized?

Sarah: By end of this week â€” Friday latest.

CTO: Great. I also want to talk about the monitoring gap. We had that P2 incident last month and our alerting was slow.

Rohan: We need to set up Datadog for the new Kubernetes cluster. That's on the backlog â€” I can start it this sprint.

CTO: Make that a priority. Action items: Sarah â€” finalize DR plan by Friday. Rohan â€” start Datadog setup this sprint. Mark â€” approve Aurora cost in finance system. Everyone â€” review security policy v2.0 sent by email.

Meeting adjourned."""
    },
    {
        "title": "Sprint Planning â€” Engineering Week 24",
        "transcript": """Scrum Master (Dev): Welcome to sprint planning for Week 24. Velocity last sprint was 47 points. Let's estimate this sprint's work.

Engineer 1 (Alex): I'll take the CI/CD pipeline setup. I estimate 8 story points â€” GitHub Actions configuration plus Docker build and push steps.

Engineer 2 (Priya): I'll continue the AWS migration. Need to focus on the database side this sprint. 13 points.

Engineer 3 (Raj): I can take the code review standards update and the ChromaDB performance optimization. Maybe 10 points total.

Dev: What about the Datadog alerting ticket?

Alex: I can do that after CI/CD. 5 points.

Dev: That brings us to 36 points. We have capacity for more.

Priya: I'd like to add a spike on vector store caching â€” we're getting slow query times on large documents. 5 points.

Dev: Approved. Raj, can you also review the security policy PR before end of week?

Raj: Yes, I'll do it by Thursday.

Dev: Great. Sprint goal: complete AWS migration database phase and ship CI/CD pipeline. Any blockers?

Alex: I need AWS credentials for the new ECR repository.

Dev: I'll request that from DevOps today. Anything else? No? Sprint starts now."""
    },
    {
        "title": "HR All-Hands â€” Q3 People Update",
        "transcript": """HR Director (Lisa): Good afternoon everyone. Thanks for joining the Q3 HR all-hands.

First topic: headcount. We're planning 6 new hires in Q3 â€” 3 engineers, 1 data scientist, 1 HR coordinator, and 1 finance analyst. All requisitions are approved in the budget.

Employee (Anita): Will the engineering hiring include frontend roles?

Lisa: Yes, two frontend engineers and one backend. Rohan's team is working on the JDs.

Lisa: Second topic: performance reviews. December cycle is coming up. We're switching from our manual process to BambooHR this year. I'll send a setup guide by end of week. All managers need to complete the training module before November.

Manager (James): Will we still use the same 5-point rating scale?

Lisa: Yes, same scale. But we're adding peer feedback as an optional component this year â€” 360-degree for senior employees.

Lisa: Third topic: the new leave policy. Parental leave is now 26 weeks for primary caregivers, up from 16. Effective immediately for all current employees.

Employee (Sonia): Does this apply retroactively for someone currently on leave?

Lisa: Yes, HR will reach out individually to anyone currently on parental leave to process the extension. No action needed from employees.

Lisa: Last item: we're launching the onboarding buddy program next month. If you'd like to volunteer as a buddy, please fill out the form I'll share in Slack #people-ops.

Lisa: Any questions? Great. Thank you all. Meeting notes will be in Confluence by tomorrow."""
    },
    {
        "title": "Security & Compliance Review â€” June 2025",
        "transcript": """CISO (David): Thank you all for joining. Today we're reviewing our security posture following the external pentest report.

Summary: We had 0 critical findings, 2 medium, 4 low, and 8 informational findings. That's a significant improvement from last year's pentest.

Medium Finding 1: JWT tokens had weak randomness in test environment. Fixed by using cryptographically secure key generation.
Medium Finding 2: Some API endpoints lacked rate limiting. We've added slowapi rate limiting in production â€” 100 requests per minute per IP.

Legal (Maya): From a GDPR standpoint, we had our annual audit last month. Two action items: update the data retention schedule and add a data breach section to the employee handbook.

David: Rohan's team is updating the retention policy this sprint. Employee handbook update is on HR's list.

Operations (Sarah): One thing I want to flag â€” we haven't tested the disaster recovery plan since Q1. We should schedule a drill.

David: Agreed. Let's put a Q3 DR drill on the calendar. I'll coordinate with Ops.

Finance (Mark): Budget question â€” the pentest firm invoice is $12,000. Is that within approved budget?

David: Yes, security pentest is a line item in the IT budget. Mark, please process against cost center ENG-002.

David: Action items: Rohan â€” update data retention policy by sprint end. HR â€” add breach notification to handbook. Sarah â€” schedule Q3 DR drill. Mark â€” process pentest invoice.

Next security review: September. Thanks everyone."""
    }
]


def seed():
    print("=" * 65)
    print("  ProcessPilot AI â€” Rich Demo Data Seeder v2")
    print("=" * 65)

    # â”€â”€ 1. Check server â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    try:
        r = requests.get(f"http://localhost:8000/health", timeout=5)
        if r.status_code == 200:
            print("\n[âœ“] Server is running")
        else:
            print("\n[âœ—] Server returned unexpected status. Continuing anyway...")
    except Exception:
        print("\n[âœ—] Cannot connect to server at http://localhost:8000")
        print("    Please start the backend first:")
        print("    cd backend && python run.py")
        sys.exit(1)

    # â”€â”€ 2. Create Departments â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[1/6] Creating departments...")
    departments = [
        {"name": "Engineering", "description": "Software Engineering, DevOps & Security"},
        {"name": "HR", "description": "Human Resources, Recruitment & People Operations"},
        {"name": "Operations", "description": "Business Operations, Vendor Management & IT"},
        {"name": "Finance", "description": "Finance, Accounting & Legal Compliance"},
    ]
    for dept in departments:
        r = requests.post(f"{BASE_URL}/auth/departments", json=dept)
        if r.status_code == 201:
            print(f"  âœ“ {dept['name']}")
        else:
            print(f"  âš  {dept['name']} may already exist")

    # â”€â”€ 3. Register Users â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[2/6] Registering demo users...")
    users = [
        {"email": "admin@processpilot.ai", "password": "admin123", "role": "Admin", "department_id": 1},
        {"email": "john@processpilot.ai", "password": "john123", "role": "Employee", "department_id": 1},
        {"email": "sarah@processpilot.ai", "password": "sarah123", "role": "Manager", "department_id": 2},
        {"email": "rohan@processpilot.ai", "password": "rohan123", "role": "Employee", "department_id": 1},
        {"email": "mark@processpilot.ai", "password": "mark123", "role": "Manager", "department_id": 4},
    ]
    for user in users:
        r = requests.post(f"{BASE_URL}/auth/register", json=user)
        if r.status_code == 201:
            print(f"  âœ“ {user['email']} ({user['role']})")
        else:
            print(f"  âš  {user['email']} may already exist")

    # â”€â”€ 4. Login as Admin â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[3/6] Authenticating as admin...")
    r = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@processpilot.ai",
        "password": "admin123"
    })
    if r.status_code != 200:
        print("  âœ— Login failed! Exiting.")
        sys.exit(1)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  âœ“ Authenticated")

    # â”€â”€ 5. Upload Documents â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print(f"\n[4/6] Uploading {len(DOCS)} documents...")
    for doc in DOCS:
        tmp_path = os.path.join(tempfile.gettempdir(), doc["filename"])
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(doc["content"])
        try:
            with open(tmp_path, "rb") as f:
                r = requests.post(
                    f"{BASE_URL}/documents/upload",
                    headers=headers,
                    files={"file": (doc["filename"], f, "text/plain")},
                    data={"department_id": str(doc["dept"])}
                )
            if r.status_code in (200, 201):
                print(f"  âœ“ {doc['filename']}")
            else:
                print(f"  âœ— {doc['filename']} â€” {r.text[:120]}")
        except Exception as e:
            print(f"  âœ— {doc['filename']} â€” {e}")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    # â”€â”€ 6. Create Tasks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print(f"\n[5/6] Creating {len(TASKS)} tasks...")
    task_ids = []
    for i, (title, desc) in enumerate(TASKS):
        r = requests.post(f"{BASE_URL}/tasks/", headers=headers, json={
            "title": title,
            "description": desc
        })
        if r.status_code in (200, 201):
            task_id = r.json().get("id")
            task_ids.append((task_id, STATUS_MAP[i]))
            print(f"  âœ“ {title}")
        else:
            print(f"  âœ— {title}")

    # Update task statuses
    print("  â†» Updating task statuses...")
    for task_id, status in task_ids:
        if task_id and status != "Pending":
            requests.patch(f"{BASE_URL}/tasks/{task_id}", headers=headers, json={"status": status})
            if status == "Completed":
                # Need 2 cycles for Pending â†’ In_Progress â†’ Completed
                requests.patch(f"{BASE_URL}/tasks/{task_id}", headers=headers, json={"status": "Completed"})

    # â”€â”€ 7. Create Meetings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print(f"\n[6/6] Creating {len(MEETINGS)} meetings...")
    for meeting in MEETINGS:
        r = requests.post(f"{BASE_URL}/meetings/", headers=headers, json=meeting)
        if r.status_code in (200, 201):
            print(f"  âœ“ {meeting['title']}")
        else:
            print(f"  âœ— {meeting['title']} â€” {r.text[:120]}")

    # â”€â”€ Done â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n" + "=" * 65)
    print("  âœ… Demo data seeded successfully!")
    print("=" * 65)
    print("""
  ðŸ”‘ Login Credentials
  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  Admin:    admin@processpilot.ai  / admin123
  Employee: john@processpilot.ai   / john123
  Manager:  sarah@processpilot.ai  / sarah123
  Employee: rohan@processpilot.ai  / rohan123
  Manager:  mark@processpilot.ai   / mark123

  ðŸ“š What was seeded
  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  Departments : 4 (Engineering, HR, Operations, Finance)
  Documents   : {doc_count} enterprise knowledge documents
  Tasks       : {task_count} (8 Pending, 5 In Progress, 9 Completed)
  Meetings    : 4 with full transcripts

  ðŸŒ Access
  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  Frontend  : http://localhost:5173
  API Docs  : http://localhost:8000/docs
  Health    : http://localhost:8000/health

  ðŸ’¡ Try these AI Copilot queries
  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  - "What is the incident response procedure for P1 outages?"
  - "How do we deploy FastAPI to Kubernetes?"
  - "What is our leave and PTO policy?"
  - "Summarize the GDPR data privacy requirements"
  - "How do we onboard new employees?"
  - "What happened in the Q3 infrastructure planning meeting?"
  - "What are our code review standards?"
""".format(doc_count=len(DOCS), task_count=len(TASKS)))


if __name__ == "__main__":
    seed()
