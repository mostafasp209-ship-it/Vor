# External project review: REA and n8n-workflows

Reviewed references:
- https://github.com/morluto/rea
- https://github.com/Zie619/n8n-workflows

## Findings

### REA
REA is an agent/MCP toolkit for reverse-engineering software and inspecting application/runtime behavior. It is not a crypto-trading strategy library, market-data provider, or signal engine. No REA runtime or dependency is added to this project because it would not improve the core trading logic directly. It could be considered later if we need authorized inspection of an exchange API/client, but API documentation and test environments should be preferred.

### n8n-workflows
The repository is a large collection of n8n automation templates, with a searchable workflow catalog and integrations. The reusable idea for this project is workflow orchestration around the trading engine: schedule health checks, consume a signed/validated signal webhook, notify Telegram/Discord/email, record alerts, and route failures to an error path. We should build our own small, reviewed workflow rather than blindly importing a large third-party JSON workflow.

## Proposed automation boundary

n8n should orchestrate notifications and monitoring, not decide whether a trade is profitable and not have direct exchange-order permissions in the first iteration.

1. Trigger: scheduled health check or webhook from the signal service.
2. Validate: reject malformed payloads, unknown symbols, stale timestamps, and duplicate signal IDs.
3. Gate: notify only when decision is LONG/SHORT and risk checks pass; otherwise log NO_TRADE.
4. Deliver: send a concise alert to Telegram/Discord or email using credentials stored in n8n credentials, never in this repository.
5. Audit: persist signal ID, model version, timestamp, and delivery result; do not log API secrets.
6. Failure path: retry bounded transient errors, then send an operational alert. Avoid infinite retries and duplicate messages.

## Example signal payload

```json
{
  "signal_id": "unique-generated-id",
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "as_of": "2026-01-01T12:00:00Z",
  "decision": "NO_TRADE",
  "confidence": null,
  "model_version": "baseline-0.1.0",
  "risk_checks_passed": false,
  "reason_codes": ["PAPER_MODE", "NOT_CALIBRATED"]
}
```

The date and values above are illustrative only. Confidence must remain null until a calibrated probability model exists; an arbitrary ensemble score must not be presented as a probability.

## Security and deployment checklist

- Keep n8n behind authentication and HTTPS; do not expose an unauthenticated webhook.
- Authenticate incoming webhooks (HMAC/signature or strong secret, timestamp, replay protection).
- Use least-privilege credentials; notification-only credentials are sufficient for alerts.
- Do not connect exchange trading keys to n8n in the research/paper-trading phase.
- Add rate limits, idempotency, payload size limits, and redacted logs.
- Pin/review imported workflow JSON and its node types before enabling it.
- Verify each workflow against the deployed n8n version and test with synthetic payloads first.

## Decision

Adopt the orchestration and notification pattern from the n8n ecosystem, but do not import unreviewed workflows wholesale. Do not add REA as a dependency. Next engineering step: implement a signal webhook contract and tests, then create and manually validate a minimal n8n notification workflow once the service endpoint and desired channel are known.
