# SCALING.md

# Scaling the AI SecOps Phishing Triage Platform to 100,000 Alerts per Day

## Overview

The current implementation is intentionally designed as a proof-of-concept focused on correctness, explainability, and ease of demonstration. It processes alerts sequentially, stores state in SQLite, and uses a locally hosted LLM through Ollama.

To support approximately 100,000 alerts per day in a production cloud environment, several architectural changes would be required. The primary challenges are throughput, LLM cost management, deduplication, observability, and fault tolerance.

---

# High-Level Architecture

Instead of processing alerts synchronously, the system would adopt an event-driven architecture.

```text
Mailbox Ingestion
        │
        ▼
 Message Queue
 (Kafka / SQS)
        │
        ▼
 Parser Workers
        │
        ▼
 Feature Extraction
        │
        ▼
 Classification Queue
        │
        ▼
 AI Analysis Workers
        │
        ▼
 Report Generation
        │
        ▼
 Analyst Dashboard
```

This approach allows each stage of the pipeline to scale independently.

---

# Queueing and Throughput

At 100,000 alerts per day, the system would process approximately:

- 4,167 alerts per hour
- 69 alerts per minute
- More during phishing campaigns or business hours

A queue-based architecture would prevent temporary traffic spikes from overwhelming downstream systems.

Potential technologies include:

- Apache Kafka
- Amazon SQS
- Google Pub/Sub

Workers can be horizontally scaled based on queue depth and processing latency.

For example:

- Parser Workers: 10 instances
- Feature Extraction Workers: 10 instances
- AI Analysis Workers: Auto-scaled based on demand

This enables the system to absorb sudden increases in alert volume without losing data.

---

# Controlling LLM Costs

The largest operational cost at scale would be LLM inference.

A naive design that sends every email to an LLM would become prohibitively expensive.

Instead, the system would implement a multi-stage analysis strategy.

## Stage 1: Deterministic Rules

Simple rules can immediately classify many alerts.

Examples:

- SPF, DKIM, and DMARC failures
- Known malicious domains
- Known benign senders
- Internal newsletters
- Duplicate alerts

Many obvious cases can be handled without invoking an LLM.

## Stage 2: Similarity Matching

A vector database or fingerprinting system can identify alerts that are nearly identical to previously analyzed messages.

If a matching alert already exists, the prior classification can be reused.

This reduces duplicate LLM requests.

## Stage 3: LLM Analysis

Only ambiguous or previously unseen alerts should be forwarded to the LLM.

This approach significantly reduces inference costs while preserving analyst value.

---

# Deduplication Strategy

Large organizations often receive hundreds or thousands of reports for the same phishing campaign.

Without deduplication, the system would repeatedly analyze identical emails.

A deduplication fingerprint can be created using:

- Sender address
- Subject
- Body content hash
- Attachment names
- URL set

Example:

```text
SHA256(
  sender +
  subject +
  body +
  urls
)
```

If the fingerprint already exists, the alert can be linked to an existing incident instead of being re-analyzed.

Benefits:

- Reduced LLM usage
- Faster triage
- Cleaner analyst workflows

---

# Observability and Monitoring

A production system requires visibility into processing health and performance.

Key metrics would include:

## Operational Metrics

- Alerts received
- Alerts processed
- Alerts failed
- Queue depth
- Processing latency

## AI Metrics

- LLM requests per minute
- LLM response latency
- JSON validation failures
- Classification distribution
- Confidence score distribution

## Security Metrics

- Critical alerts generated
- Escalation rate
- Top phishing campaigns
- Most targeted departments

Metrics would be collected using Prometheus and visualized through Grafana dashboards.

Automated alerts would notify engineers if:

- Queue depth exceeds thresholds
- LLM failures increase
- Processing latency spikes
- Critical services become unavailable

---

# Handling Partial Failures

Failure handling is critical in distributed systems.

The platform should assume that individual components will fail.

Examples include:

- LLM timeouts
- Database outages
- Network interruptions
- Malformed email data

## Retry Strategy

Transient failures should be retried automatically with exponential backoff.

Examples:

- Temporary API failures
- Service interruptions
- Network latency issues

## Dead Letter Queue

Alerts that repeatedly fail processing should be moved to a Dead Letter Queue (DLQ).

This prevents a single problematic alert from blocking the pipeline.

Engineers can review DLQ entries separately.

## Graceful Degradation

If the AI analysis service becomes unavailable:

- Store the alert
- Mark status as Pending Analysis
- Notify operators
- Resume processing once service recovers

This ensures no alert data is lost.

---

# Data Storage

SQLite is sufficient for a proof-of-concept but would not support production-scale workloads.

Potential production alternatives include:

- PostgreSQL
- Amazon Aurora
- Google Cloud SQL

Frequently accessed data such as deduplication fingerprints and active incidents could be cached using Redis.

---

# Security Considerations

Because phishing reports may contain sensitive corporate information, production deployments should implement:

- Encryption at rest
- Encryption in transit
- Role-based access control
- Audit logging
- Secret management through a vault solution
- Data retention policies

All LLM interactions should be logged and monitored to support investigation and compliance requirements.

---

# Conclusion

The primary scaling challenge is not ingestion or storage, but efficiently handling AI analysis at high volume. A production implementation would therefore prioritize:

1. Queue-based processing
2. Aggressive deduplication
3. Rule-based pre-filtering
4. Selective LLM usage
5. Comprehensive observability
6. Fault-tolerant workflows

These changes would allow the platform to process approximately 100,000 alerts per day while maintaining reasonable operational costs, reliability, and analyst effectiveness.
