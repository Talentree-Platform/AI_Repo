# 🤖 Talentree Recommendation System — API Integration Guide
> **For Backend Team Use**  
> Production-Grade Enterprise Dual Recommendation System  
> FastAPI · SQL Server · MLflow · Docker · Railway

---

## 🌐 Base URL

```
https://deployedrecommendationsystem-production.up.railway.app
```

All endpoints are relative to this base URL.

---

## 🔐 Authentication

All `/recommend` endpoints are **protected**. The caller must include a valid JWT Bearer token issued by the Talentree ASP.NET API.

### How it works
The API reads the `Authorization` header, decodes the JWT, verifies it (signature, expiry, issuer, audience), and extracts the user UUID from the `sub` claim **server-side**. The client does **not** send a `customer_id` or `owner_id` in the request body.

### Required Header (for protected endpoints)

```
Authorization: Bearer <access_token>
```

| Header | Value | Required on |
|---|---|---|
| `Authorization` | `Bearer <JWT_token>` | `/customer/recommend`, `/owner/recommend` |
| `Content-Type` | `application/json` | All POST requests |
| `Accept` | `application/json` | Recommended |

### Token Requirements

| Property | Expected Value |
|---|---|
| Algorithm | `HS256` |
| Issuer (`iss`) | `TalentreeApi` |
| Audience (`aud`) | `TalentreeClient` |
| User ID Claim | `sub` (UUID string) |

> [!NOTE]
> The token issued by the existing Talentree ASP.NET API is already compatible — no changes needed on the token side. Just pass it as-is in the `Authorization` header.

---

## 📋 Endpoint Overview

| # | Method | Route | Auth Required | Description |
|---|---|---|---|---|
| 1 | `GET` | `/health` | ❌ No | Global system health check |
| 2 | `GET` | `/customer/health` | ❌ No | Customer service health check |
| 3 | `GET` | `/customer/list` | ❌ No | Get list of all customers |
| 4 | `POST` | `/customer/recommend` | ✅ **Yes** | Get product recommendations for the authenticated customer |
| 5 | `GET` | `/customer/model-info` | ❌ No | Get customer model metadata |
| 6 | `POST` | `/customer/retrain` | ❌ No | Trigger customer model retraining |
| 7 | `GET` | `/owner/health` | ❌ No | Owner service health check |
| 8 | `GET` | `/owner/list` | ❌ No | Get list of all business owners |
| 9 | `POST` | `/owner/recommend` | ✅ **Yes** | Get procurement recommendations for the authenticated owner |
| 10 | `GET` | `/owner/model-info` | ❌ No | Get owner model metadata |
| 11 | `POST` | `/owner/retrain` | ❌ No | Trigger owner model retraining |

---

## 🌍 Global Endpoints

---

### 1. `GET /health`

**Full URL:** `https://deployedrecommendationsystem-production.up.railway.app/health`

**Description:** Top-level system health check. Returns the status of the database connection and both AI models.

**Request Body:** None

**Response — `200 OK`:**
```json
{
  "status": "healthy",
  "app": "Enterprise Recommendation System",
  "environment": "production",
  "database_connected": true,
  "customer_model_loaded": true,
  "owner_model_loaded": true
}
```

| Field | Type | Description |
|---|---|---|
| `status` | `string` | Always `"healthy"` if server is up |
| `app` | `string` | Application name |
| `environment` | `string` | Deployment environment |
| `database_connected` | `boolean` | Whether SQL Server is reachable |
| `customer_model_loaded` | `boolean` | Whether the customer ML model is in memory |
| `owner_model_loaded` | `boolean` | Whether the owner ML model is in memory |

---

## 🛒 Customer Recommender Endpoints

---

### 2. `GET /customer/health`

**Full URL:** `https://deployedrecommendationsystem-production.up.railway.app/customer/health`

**Auth Required:** ❌ No

**Response — `200 OK`:**
```json
{
  "status": "healthy",
  "service": "customer_recommender",
  "model_status": "active"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | `string` | Always `"healthy"` if service is up |
| `service` | `string` | Always `"customer_recommender"` |
| `model_status` | `string` | `"active"` if ML model loaded, `"fallback_popular"` otherwise |

---

### 3. `GET /customer/list`

**Full URL:** `https://deployedrecommendationsystem-production.up.railway.app/customer/list`

**Auth Required:** ❌ No

**Description:** Returns a list of all B2C customers from SQL Server (or demo fallback).

**Response — `200 OK`:**
```json
[
  { "user_id": "11111111-1111-1111-1111-111111111101", "name": "Nour Elsayed" },
  { "user_id": "11111111-1111-1111-1111-111111111102", "name": "Ahmed Ali" }
]
```

---

### 4. `POST /customer/recommend` ⭐ 🔒

**Full URL:** `https://deployedrecommendationsystem-production.up.railway.app/customer/recommend`

**Auth Required:** ✅ **Yes — JWT Bearer token**

**Description:** Returns a personalized ranked list of product recommendations for the **currently authenticated customer**. The customer identity is extracted from the JWT token — the client does **not** send a `customer_id`.

**Request Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "top_k": 6
}
```

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `top_k` | `integer` | ❌ No (default: `6`) | Min: `1`, Max: `50` | Number of product recommendations to return |

> [!IMPORTANT]
> `customer_id` is **no longer in the request body**. It is automatically extracted server-side from the `sub` claim of the JWT token.

**Response — `200 OK`:**
```json
{
  "customer_id": "11111111-1111-1111-1111-111111111101",
  "recommendations": [
    {
      "product_id": 42,
      "product_name": "Handmade Linen Tote Bag",
      "category": "Fashion & Accessories",
      "price": 29.99,
      "description": "Eco-friendly handcrafted linen tote bag.",
      "score": 0.9231
    }
  ],
  "model_version": "2026-06-15 10:22:01"
}
```

| Field | Type | Description |
|---|---|---|
| `customer_id` | `string` | UUID of the authenticated customer (from JWT) |
| `recommendations` | `array` | Ordered list of recommended products (highest score first) |
| `recommendations[].product_id` | `integer` | Unique product identifier |
| `recommendations[].product_name` | `string` | Display name of the product |
| `recommendations[].category` | `string` | Product category |
| `recommendations[].price` | `float` | Product price |
| `recommendations[].description` | `string` | Short product description |
| `recommendations[].score` | `float` | Relevance score (higher = more relevant) |
| `model_version` | `string` | Timestamp of the active model |

**Error Responses:**

| Status | Description |
|---|---|
| `401 Unauthorized` | Missing, expired, or invalid JWT token |
| `403 Forbidden` | Token valid but user ID claim absent |
| `500 Internal Server Error` | Model inference failure |

---

### 5. `GET /customer/model-info`

**Full URL:** `https://deployedrecommendationsystem-production.up.railway.app/customer/model-info`

**Auth Required:** ❌ No

**Description:** Returns metadata about the currently loaded customer ML model.

**Response — `200 OK`:**
```json
{
  "model_file": "./trained_models/customer/latest/customer_model.joblib",
  "last_modified": "2026-06-15 10:22:01",
  "num_users": 500,
  "num_products": 100,
  "top_k_default": 6
}
```

---

### 6. `POST /customer/retrain`

**Full URL:** `https://deployedrecommendationsystem-production.up.railway.app/customer/retrain`

**Auth Required:** ❌ No

**Description:** Triggers non-blocking background retraining of the customer model. Returns immediately.

**Request Body:** None (empty POST)

**Response — `200 OK`:**
```json
{
  "success": true,
  "message": "Customer model retraining started in the background."
}
```

---

## 💼 Owner (Business Procurement) Recommender Endpoints

---

### 7. `GET /owner/health`

**Full URL:** `https://deployedrecommendationsystem-production.up.railway.app/owner/health`

**Auth Required:** ❌ No

**Response — `200 OK`:**
```json
{
  "status": "healthy",
  "service": "owner_recommender",
  "model_status": "active"
}
```

---

### 8. `GET /owner/list`

**Full URL:** `https://deployedrecommendationsystem-production.up.railway.app/owner/list`

**Auth Required:** ❌ No

**Description:** Returns a list of all registered business owners from SQL Server (or demo fallback).

**Response — `200 OK`:**
```json
[
  { "owner_id": "11111111-1111-1111-1111-111111111101", "name": "Tech Galaxy" },
  { "owner_id": "11111111-1111-1111-1111-111111111102", "name": "Fashion House" }
]
```

---

### 9. `POST /owner/recommend` ⭐ 🔒

**Full URL:** `https://deployedrecommendationsystem-production.up.railway.app/owner/recommend`

**Auth Required:** ✅ **Yes — JWT Bearer token**

**Description:** Returns a ranked list of raw material procurement recommendations for the **currently authenticated business owner**. The owner identity is extracted from the JWT token — the client does **not** send an `owner_id`.

**Request Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "top_k": 6
}
```

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `top_k` | `integer` | ❌ No (default: `6`) | Min: `1`, Max: `50` | Number of procurement recommendations to return |

> [!IMPORTANT]
> `owner_id` is **no longer in the request body**. It is automatically extracted server-side from the `sub` claim of the JWT token.

**Response — `200 OK`:**
```json
{
  "owner_id": "11111111-1111-1111-1111-111111111101",
  "recommendations": [
    {
      "material_id": 12,
      "material_name": "Premium Cotton Fabric",
      "category": "Textiles",
      "price": 4.75,
      "description": "High-thread-count cotton fabric for garment production.",
      "predicted_demand_qty": 320.5,
      "urgency_days_elapsed": 28,
      "urgency_cycle_days": 30,
      "score": 0.8741
    }
  ],
  "model_version": "2026-06-15 10:22:01"
}
```

| Field | Type | Description |
|---|---|---|
| `owner_id` | `string` | UUID of the authenticated business owner (from JWT) |
| `recommendations` | `array` | Ordered list of procurement recommendations (highest score first) |
| `recommendations[].material_id` | `integer` | Unique raw material identifier |
| `recommendations[].material_name` | `string` | Display name of the material |
| `recommendations[].category` | `string` | Material category |
| `recommendations[].price` | `float` | Unit price |
| `recommendations[].description` | `string` | Short material description |
| `recommendations[].predicted_demand_qty` | `float` | ML-predicted demand quantity for the next cycle |
| `recommendations[].urgency_days_elapsed` | `integer` | Days since last reorder |
| `recommendations[].urgency_cycle_days` | `integer` | Expected full reorder cycle duration (days) |
| `recommendations[].score` | `float` | Procurement urgency score (higher = more urgent) |
| `model_version` | `string` | Timestamp of the active model |

**Error Responses:**

| Status | Description |
|---|---|
| `401 Unauthorized` | Missing, expired, or invalid JWT token |
| `403 Forbidden` | Token valid but user ID claim absent |
| `500 Internal Server Error` | Model inference failure |

---

### 10. `GET /owner/model-info`

**Full URL:** `https://deployedrecommendationsystem-production.up.railway.app/owner/model-info`

**Auth Required:** ❌ No

**Response — `200 OK`:**
```json
{
  "model_file": "./trained_models/owner/latest/owner_model.joblib",
  "last_modified": "2026-06-15 10:22:01",
  "num_owners": 100,
  "num_materials": 50,
  "top_k_default": 6
}
```

---

### 11. `POST /owner/retrain`

**Full URL:** `https://deployedrecommendationsystem-production.up.railway.app/owner/retrain`

**Auth Required:** ❌ No

**Description:** Triggers non-blocking background retraining of the owner procurement model.

**Request Body:** None (empty POST)

**Response — `200 OK`:**
```json
{
  "success": true,
  "message": "Owner model retraining started in the background."
}
```

---

## ⚡ Integration Examples

### JavaScript (fetch)

```javascript
const token = "eyJhbGciOiJIUzI1NiIs..."; // JWT from your login response

// Customer Recommendations
const response = await fetch(
  'https://deployedrecommendationsystem-production.up.railway.app/customer/recommend',
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ top_k: 6 })
  }
);
const data = await response.json();
console.log(data.recommendations);
```

```javascript
// Owner Procurement Recommendations
const response = await fetch(
  'https://deployedrecommendationsystem-production.up.railway.app/owner/recommend',
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ top_k: 6 })
  }
);
const data = await response.json();
console.log(data.recommendations);
```

### C# (HttpClient)

```csharp
var client = new HttpClient();
client.DefaultRequestHeaders.Authorization =
    new AuthenticationHeaderValue("Bearer", accessToken);

var body = JsonSerializer.Serialize(new { top_k = 6 });
var content = new StringContent(body, Encoding.UTF8, "application/json");

// Customer
var response = await client.PostAsync(
    "https://deployedrecommendationsystem-production.up.railway.app/customer/recommend",
    content
);
var result = await response.Content.ReadAsStringAsync();

// Owner
var response = await client.PostAsync(
    "https://deployedrecommendationsystem-production.up.railway.app/owner/recommend",
    content
);
```

### Python (requests)

```python
import requests

token = "eyJhbGciOiJIUzI1NiIs..."  # JWT from login
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Customer
resp = requests.post(
    "https://deployedrecommendationsystem-production.up.railway.app/customer/recommend",
    json={"top_k": 6},
    headers=headers
)
print(resp.json())

# Owner
resp = requests.post(
    "https://deployedrecommendationsystem-production.up.railway.app/owner/recommend",
    json={"top_k": 6},
    headers=headers
)
print(resp.json())
```

---

## 🖥️ Interactive API Docs (Swagger UI)

FastAPI auto-generates interactive documentation with a 🔒 padlock icon on protected endpoints:

| Tool | URL |
|---|---|
| **Swagger UI** | [`/docs`](https://deployedrecommendationsystemproduction.up.railway.app/docs) |
| **ReDoc** | [`/redoc`](https://deployedrecommendationsystemproduction.up.railway.app/redoc) |
| **OpenAPI JSON** | [`/openapi.json`](https://deployedrecommendationsystemproduction.up.railway.app/openapi.json) |

> To test protected endpoints on Swagger UI: click the **Authorize 🔒** button at the top → paste your Bearer token.

---

## ❗ Error Reference

| HTTP Status | Meaning | When It Happens |
|---|---|---|
| `200 OK` | Success | Request processed correctly |
| `401 Unauthorized` | Authentication failed | Missing `Authorization` header, expired token, invalid signature, wrong issuer/audience |
| `403 Forbidden` | Token valid, claim missing | JWT decoded fine but `sub` claim not present |
| `422 Unprocessable Entity` | Validation error | Request body has wrong field types |
| `500 Internal Server Error` | Server-side failure | Model inference crashed |

### Example `401` Response
```json
{
  "detail": "Token validation failed: Signature has expired."
}
```

### Example `422` Response
```json
{
  "detail": [
    {
      "type": "int_parsing_error",
      "loc": ["body", "top_k"],
      "msg": "Input should be a valid integer",
      "input": "six"
    }
  ]
}
```

---

## 📝 Key Notes for the BE Team

> [!IMPORTANT]
> - **No user IDs in the body anymore.** `customer_id` and `owner_id` have been removed from the `/recommend` request bodies. The server reads the user UUID from the `sub` claim of the JWT automatically.
> - **Just pass the existing Talentree JWT token** in the `Authorization: Bearer` header — no changes needed to how tokens are generated.
> - `top_k` is optional (defaults to `6`). Set it to however many results your UI needs (max `50`).
> - If the user UUID from the token is **not found** in the training data, the system gracefully falls back to globally popular items — it will **not** return an error.
> - The `/retrain` endpoints are safe to call anytime — they are non-blocking and won't disrupt active recommendation requests.
> - CORS is fully open — no preflight issues from any frontend origin.

---

*Talentree AI Platform © 2026 | Production Grade MLOps Architecture*
