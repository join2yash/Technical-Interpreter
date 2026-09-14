# Data Privacy, Control, and Governance

## Status

This document defines mandatory data-governance rules for the Technical Interpreter. These rules apply from the MVP onward and must remain true as the system gains AI, persistence, retrieval, and learning capabilities.

## Core rule: case isolation

**Case-specific information must never be used as factual evidence for another case.**

Information from User/Case A may not be disclosed, retrieved, inferred, or reused as a factual detail in User/Case B's response.

Example:

- Case A explicitly states that an SSL certificate/licence expired.
- Case B only states that there was a licensing-related issue.
- The system must not add "SSL certificate" to Case B unless Case B independently provides evidence for it.

## Three data classes

### 1. Case data

Facts supplied or confirmed for one technical case. Examples include incidents, environments, systems, users, teams, configurations, causes, actions, and verification results.

Case data is private to its case scope and must not become general knowledge merely because it was processed.

### 2. General knowledge

Non-case-specific concepts, terminology, definitions, relationships, and language patterns that can help interpret technical text.

General knowledge may support interpretation, but it must never be treated as evidence of a fact in a specific case.

### 3. System-improvement signals

Aggregated or appropriately de-identified signals used to improve questions, terminology handling, or system behavior.

System-improvement signals must not contain reusable case facts that could identify or reconstruct a user's case.

## Provenance requirement

The architecture should maintain provenance for information used in interpretation. At minimum, the system must distinguish:

- user-provided case evidence
- user-provided clarification evidence
- general system knowledge
- model-generated interpretation

A generated statement about a case must be traceable to current-case evidence. General knowledge can explain or organize information, but cannot fill an unsupported factual gap.

## No cross-case factual completion

The interpreter must not complete missing case information from:

- previous users
- previous cases
- other organizations
- other conversations
- retrieved case records
- learned examples

If the current case does not contain the required fact, the interpreter must ask for clarification or leave the fact unknown.

## Data minimization

Only information necessary for the selected documentation sections should be processed for the current interaction. The system should avoid collecting unrelated personal or technical information.

## Learning policy

The MVP does not train or update a model from user responses. Future learning features must use an explicit governed pipeline that separates generalizable knowledge from case data.

A response may contribute to general system improvement only after the applicable privacy, authorization, de-identification, and governance controls permit it. Case facts must not be promoted into general knowledge simply because they are technically useful.

## Storage and retention

The current text MVP is stateless at the application layer: it does not require a persistent case database to perform interpretation, clarification, or documentation generation.

Future persistent storage must define retention, deletion, access control, encryption, tenant/case isolation, auditability, and export before it is introduced.

## External AI providers

When an external model/API is introduced, the system must explicitly define what data is sent outside the application boundary, under what authorization, for what purpose, and under what retention terms. Sensitive case data must not be sent to an external provider by default merely because an AI feature is available.

## Output safety

The final documentation generator must use only information authorized and available for the current case. It must not introduce facts from other cases, even when those facts appear highly plausible or technically related.

The system should prefer an explicit unknown or a clarification question over an unsupported statement.

## Required future controls

Before adding persistent learning, multi-user retrieval, or external LLM processing, the project should implement and test:

1. Case/tenant isolation
2. Data classification
3. Provenance tracking
4. Access control
5. Retention and deletion controls
6. Audit logging without unnecessary sensitive payloads
7. Controlled learning/knowledge-ingestion pipeline
8. De-identification where applicable
9. External-provider data policy
10. Cross-case leakage tests

## Non-negotiable acceptance test

If Case A contains a fact that Case B does not contain, a response generated for Case B must not contain that fact as though it were known for Case B.
