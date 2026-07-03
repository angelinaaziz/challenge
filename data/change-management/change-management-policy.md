# Change Management Policy

## Overview
All changes to production systems must follow this policy. It defines the documentation, approval, testing, and deployment requirements for standard, normal, and emergency changes.

## Change Categories

| Category | Definition | Minimum approvers | CAB required |
| --- | --- | --- | --- |
| Standard | Pre-authorised, low-risk, repeatable change from the standard change catalog | 1 (Change Coordinator) | No |
| Normal | Non-routine change with a defined risk assessment | 2 (Change Coordinator + Change Approver from CAB) | Yes |
| Emergency | Change required within 4 hours to restore or protect a production service | 1 (Duty Change Approver), retrospective CAB review within 5 business days | Retrospective |

## Required Documentation
Every change (regardless of category) must include:
- A change request identifier (e.g. CHG-YYYY-NNNN)
- Scope: systems affected, code repositories, config surfaces
- Risk classification (Low / Medium / High)
- Rollback plan
- Named requester and named approver
- Planned start and end times

## Approval Rules
- The approver must be a different named human from the requester (four-eyes principle).
- Approvers must hold the Change Approver role in the identity provider.
- Approval must occur **before** the deployment window opens.
- Retrospective approvals are only valid for Emergency changes and must be documented as such.

## Testing Requirements
- Standard and Normal changes: pre-deployment testing evidence (test plan + test results) must be attached to the change request.
- Emergency changes: post-deployment verification test evidence must be captured within 24 hours.
- Testing must include, at minimum, functional smoke tests of the affected surfaces.
- Failed tests block deployment for Standard/Normal changes; must be documented as accepted risk for Emergency changes.

## Deployment
- Deployment must occur within the approved change window.
- All deployment activity must produce a deployment log with timestamps and executor identity.
- Post-deployment monitoring for 60 minutes minimum.

## Exceptions
The following are out of scope:
- Documentation-only changes (README, comments)
- Break-fix hotfixes classified as Incident Response (see Incident Response Policy)
- Changes to development or staging environments

---
**Last Updated**: 2026-03-01
**Policy Owner**: Head of Platform Engineering
**Review Frequency**: Annually
