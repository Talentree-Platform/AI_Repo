# Talentree AI Service — Backend Integration Guide
## For: .NET Backend Team
**AI Service URL:** https://memo620-talentree-ai.hf.space
**Swagger UI:** https://memo620-talentree-ai.hf.space/docs
**Date:** June 2026

---

## How Integration Works

All AI calls should be **fire-and-forget** (non-blocking).
The AI service writes results **directly back to the database**.
The .NET backend does NOT need to read the AI response — just trigger the call and move on.

```
User Action → .NET saves to DB → .NET fires AI call (background) → AI updates DB → Frontend reads updated values
```

---

## Event → Endpoint Map

### 1. BO Logs In
**Trigger:** After `LoginHistory` record is saved to DB
```
POST https://memo620-talentree-ai.hf.space/ai/predict/churn/{bo_user_id}
```
**Effect:** Updates `AspNetUsers.ChurnRiskScore` + `ChurnRiskUpdatedAt`

---

### 2. BO Saves / Updates Profile
**Trigger:** After `BusinessOwnerProfile` UPDATE is committed
```
POST https://memo620-talentree-ai.hf.space/ai/compute/profile/{bo_user_id}
```
**Effect:** Updates `BusinessOwnerProfile.ProfileCompletenessPct`

---

### 3. BO Creates a New Product
**Trigger:** After `Products` INSERT is committed
```
POST https://memo620-talentree-ai.hf.space/ai/compute/product/{product_id}
```
**Effect:** Updates `Products.DescriptionQualityScore`, `DemandForecastQty`, `LowStockFlag`

---

### 4. BO Updates a Product (title, description, price, stock)
**Trigger:** After `Products` UPDATE is committed
```
POST https://memo620-talentree-ai.hf.space/ai/compute/product/{product_id}
```
**Effect:** Same as above — recalculates quality + demand + stock flag

---

### 5. New Production Request Submitted
**Trigger:** After `BoProductionRequests` INSERT — before admin reviews it
```
POST https://memo620-talentree-ai.hf.space/ai/predict/fraud/{request_id}
```
**Effect:** Updates `BoProductionRequests.FraudScore` + `IsFraudFlag`

---

### 6. Production Request Status → Completed
**Trigger:** After status UPDATE to `Completed`
```
POST https://memo620-talentree-ai.hf.space/ai/compute/request/{request_id}
```
**Effect:** Updates `BoProductionRequests.FulfillmentHours` + re-checks fraud score

---

### 7. Customer Submits a Product Review
**Trigger:** After `ProductReviews` INSERT
```
POST https://memo620-talentree-ai.hf.space/ai/predict/sentiment/{review_id}
```
**Effect:** Updates `ProductReviews.SentimentScore` + `SentimentLabel`
Labels: `"Positive"`, `"Neutral"`, `"Negative"`

---

### 8. Support Ticket Opened
**Trigger:** After `SupportTickets` INSERT
```
POST https://memo620-talentree-ai.hf.space/ai/predict/triage/{ticket_id}
```
**Effect:** Updates `SupportTickets.AutoCategory` + `PriorityScore`
Categories: `Payment`, `ProductQuality`, `Delivery`, `Account`, `Technical`
Priority: `Low`, `Medium`, `High`, `Critical`

---

### 9. Financial Transaction Recorded
**Trigger:** After `Transactions` INSERT
```
POST https://memo620-talentree-ai.hf.space/ai/predict/anomaly/{tx_id}
```
**Effect:** Updates `Transactions.AnomalyScore` + `AnomalyFlag`

---

## C# Implementation (Copy-Paste Ready)

```csharp
// AiServiceClient.cs
public class AiServiceClient
{
    private readonly HttpClient _http;
    private const string AI_BASE = "https://memo620-talentree-ai.hf.space";

    public AiServiceClient(HttpClient http)
    {
        _http = http;
    }

    // Fire-and-forget helper — never blocks the main request
    private void FireAndForget(string url)
    {
        Task.Run(async () =>
        {
            try { await _http.PostAsync(url, null); }
            catch { /* log silently — never crash main flow */ }
        });
    }

    public void OnBoLogin(string boUserId)
        => FireAndForget($"{AI_BASE}/ai/predict/churn/{boUserId}");

    public void OnProfileUpdated(string boUserId)
        => FireAndForget($"{AI_BASE}/ai/compute/profile/{boUserId}");

    public void OnProductSaved(int productId)
        => FireAndForget($"{AI_BASE}/ai/compute/product/{productId}");

    public void OnProductionRequestCreated(int requestId)
        => FireAndForget($"{AI_BASE}/ai/predict/fraud/{requestId}");

    public void OnProductionRequestCompleted(int requestId)
        => FireAndForget($"{AI_BASE}/ai/compute/request/{requestId}");

    public void OnReviewCreated(int reviewId)
        => FireAndForget($"{AI_BASE}/ai/predict/sentiment/{reviewId}");

    public void OnSupportTicketCreated(int ticketId)
        => FireAndForget($"{AI_BASE}/ai/predict/triage/{ticketId}");

    public void OnTransactionCreated(int txId)
        => FireAndForget($"{AI_BASE}/ai/predict/anomaly/{txId}");
}
```

---

## Where to Inject These Calls

| Service/Controller | Method | Call |
|---|---|---|
| `AuthService` | `LoginAsync()` — after success | `OnBoLogin(userId)` |
| `BusinessOwnerProfileService` | `UpdateProfileAsync()` — after SaveChanges | `OnProfileUpdated(boId)` |
| `ProductService` | `CreateProductAsync()` — after SaveChanges | `OnProductSaved(productId)` |
| `ProductService` | `UpdateProductAsync()` — after SaveChanges | `OnProductSaved(productId)` |
| `ProductionRequestService` | `CreateRequestAsync()` — after SaveChanges | `OnProductionRequestCreated(requestId)` |
| `ProductionRequestService` | `UpdateStatusAsync()` when status = Completed | `OnProductionRequestCompleted(requestId)` |
| `ReviewService` | `CreateReviewAsync()` — after SaveChanges | `OnReviewCreated(reviewId)` |
| `SupportTicketService` | `CreateTicketAsync()` — after SaveChanges | `OnSupportTicketCreated(ticketId)` |
| `TransactionService` | `CreateTransactionAsync()` — after SaveChanges | `OnTransactionCreated(txId)` |

---

## Register HttpClient in DI (Program.cs)

```csharp
builder.Services.AddHttpClient<AiServiceClient>(client =>
{
    client.Timeout = TimeSpan.FromSeconds(30);
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});
```

---

## Important Notes

1. **Never await AI calls** — they are background enrichment, not required for the user's response
2. **AI writes directly to DB** — no need to read AI responses or parse JSON
3. **Frontend reads from DB** — via normal .NET API endpoints (GET /products, etc.)
4. **Nightly auto-update** — even without event calls, the scheduler recomputes everything at 02:00 AM Cairo daily
5. **No auth needed** — the AI service is internal; no API key required from .NET

---

## Summary Flow Diagram

```
BO logs in
    └─► .NET saves LoginHistory
           └─► FireAndForget → POST /ai/predict/churn/{id}
                    └─► AI reads login patterns
                           └─► AI updates ChurnRiskScore in DB
                                    └─► Angular reads score via .NET GET /profile

New review submitted
    └─► .NET saves ProductReviews
           └─► FireAndForget → POST /ai/predict/sentiment/{id}
                    └─► AI runs VADER NLP
                           └─► AI updates SentimentScore + SentimentLabel in DB
                                    └─► Angular reads sentiment via .NET GET /reviews

New transaction
    └─► .NET saves Transactions
           └─► FireAndForget → POST /ai/predict/anomaly/{id}
                    └─► AI runs Isolation Forest
                           └─► AI updates AnomalyScore + AnomalyFlag in DB
                                    └─► Angular shows alert badge if flagged
```
