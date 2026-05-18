# Wraith product telemetry spec

For the cost-vs-value report to have a real value side, Wraith needs to log every AI-touched field on every case.

## Schema

New Prisma model `AiActionEvent`. Tenant-scoped per Wraith CLAUDE.md rule 8.

```prisma
model AiActionEvent {
  id            String   @id @default(uuid()) @db.UniqueIdentifier
  tenantId     String   @db.UniqueIdentifier
  tenant       Tenant   @relation(fields: [tenantId], references: [id])
  featureKey   String   @db.NVarChar(64)   // 'email-intake', 'allegation-draft', etc.
  issueNumber  Int                          // the GitHub issue this feature traces to
  caseId       String?  @db.UniqueIdentifier
  fieldName    String   @db.NVarChar(120)
  aiValue      String?  @db.NVarChar(MAX)
  humanValue   String?  @db.NVarChar(MAX)
  outcome      AiOutcome
  secondsSaved Int?
  createdAt    DateTime @default(now())

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

Already partial in email-intake (`EmailIntakePage.tsx` tracks accepted/edited per field). Generalise:

1. **Service-side helper** `AiActionLogger.log({ featureKey, issueNumber, fieldName, aiValue, humanValue, outcome, caseId? })`. Tenant pulled from CLS request context (same pattern Wraith uses elsewhere).
2. **Frontend hook** `useAiActionLogger(featureKey, issueNumber)`. Fires on field accept/edit/reject. Debounced.

## Endpoint

```
POST /ai/action-event
GET  /admin/ai-value-report?tenant=<id>&since=<iso>&until=<iso>
```

`GET /admin/ai-value-report` returns:

```json
{
  "tenantId": "...",
  "window": { "since": "...", "until": "..." },
  "features": [
    {
      "featureKey": "email-intake",
      "issueNumber": 8579,
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

## Permission

`@RequiresPermission('AdminAiReport')` per Wraith coding standard rule 12. Permission constant in registry.

## avt integration

Once endpoint exists, `avt.telemetry` fetches the JSON, converts to `value.csv` rows where `value_score = accepted * 1.0 + edited * 0.4` per feature.

## Rollout

1. Schema migration + model. One PR, schema-only.
2. Logger helper + endpoint + permission. One PR.
3. Wire email-intake hook points. One PR.
4. Wire each subsequent AI feature as it ships. Standing pattern.

## Non-goals

- No cross-tenant aggregation in v1. Per-tenant only.
- No PII in `aiValue` / `humanValue` storage. If a field is PII-sensitive, store a hash, not the value.
