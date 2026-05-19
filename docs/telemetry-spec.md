# Product telemetry spec

The placeholder `value_score = lines + (merged_prs × 200)` in `report.py` is a code-volume proxy. To turn it into a real customer-value number, instrument your product to log every AI-touched field.

Below is a reference schema. Adapt to your stack (Prisma example, but the shape is generic).

## Schema

```prisma
model AiActionEvent {
  id            String   @id @default(uuid())
  tenantId      String                          // tenant-scoped — never leak across customers
  featureKey    String                          // 'email-intake', 'recommendation-draft', etc.
  issueNumber   Int                             // GitHub/Jira issue this feature traces to
  caseId        String?                         // domain entity id, if applicable
  fieldName     String                          // which field on the artefact
  aiValue       String?                         // what the AI produced
  humanValue    String?                         // what the human kept
  outcome       AiOutcome                       // Accepted | Edited | Rejected
  secondsSaved  Int?                            // optional estimate
  createdAt     DateTime @default(now())

  @@index([tenantId, featureKey, createdAt])
  @@index([issueNumber])
}

enum AiOutcome {
  Accepted
  Edited
  Rejected
}
```

## Hook points

1. **Service-side helper** `AiActionLogger.log({ featureKey, issueNumber, fieldName, aiValue, humanValue, outcome })`. Pull tenant from your request context.
2. **Frontend hook** `useAiActionLogger(featureKey, issueNumber)`. Fires on field accept / edit / reject. Debounced.

## Endpoint

```
POST /ai/action-event
GET  /admin/ai-value-report?tenant=<id>&since=<iso>&until=<iso>
```

Response:

```json
{
  "tenantId": "...",
  "window": { "since": "...", "until": "..." },
  "features": [
    {
      "featureKey": "email-intake",
      "issueNumber": 1042,
      "events": 412,
      "accepted": 348,
      "edited": 51,
      "rejected": 13,
      "accept_rate": 0.84,
      "estimated_seconds_saved": 9870
    }
  ]
}
```

## avt integration

Once the endpoint exists, `avt.telemetry` fetches the JSON and converts to `value.csv` rows where `value_score = accepted * 1.0 + edited * 0.4` per feature.

## Rollout

1. Schema migration + model. One PR, schema only.
2. Logger helper + endpoint + permission. One PR.
3. Wire the first AI feature. One PR.
4. Wire each subsequent AI feature as it ships. Standing pattern.

## Non-goals

- No cross-tenant aggregation by default. Per-tenant only.
- No PII in `aiValue` / `humanValue`. Hash sensitive fields.
