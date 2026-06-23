"""
Admin RFM Service — Model 9 (NEW)
====================================
Customer RFM Segmentation using K-Means clustering.

RFM = Recency, Frequency, Monetary
  R — days since last CustomerOrders row
  F — count of CustomerOrders rows
  M — sum of CustomerOrders.TotalAmount

Segments (4 clusters):
  Champion  — high F, high M, low R
  Loyal     — medium F & M, low-medium R
  At Risk   — was good, now high R
  Lost      — low on all 3

Writes result to AspNetUsers.RfmSegment (backend must add this column).
Falls back to rule-based when < 10 customers have orders.
"""
import os
import pickle
import numpy as np
from datetime import datetime

MODELS_DIR  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
RFM_MODEL_PATH = os.path.join(MODELS_DIR, "admin_rfm_model.pkl")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rule_based_segment(r: float, f: int, m: float) -> str:
    """Simple rule-based fallback when data is insufficient for K-Means."""
    if r <= 30 and f >= 2 and m >= 500:
        return "Champion"
    elif r <= 60 and f >= 1:
        return "Loyal"
    elif r <= 180:
        return "At Risk"
    return "Lost"


def _map_clusters_to_labels(centers: np.ndarray) -> dict:
    """
    Map K-Means cluster IDs to human-readable labels.
    We rank clusters by composite score: -R + F + M (normalised).
    Highest → Champion, then Loyal, then At Risk, lowest → Lost.
    """
    # Normalise each feature column across cluster centres
    mins  = centers.min(axis=0)
    maxs  = centers.max(axis=0)
    denom = np.where((maxs - mins) == 0, 1, maxs - mins)
    norm  = (centers - mins) / denom  # shape (4, 3)

    # Score = -Recency + Frequency + Monetary  (R is inverted)
    scores = -norm[:, 0] + norm[:, 1] + norm[:, 2]
    ranked = np.argsort(scores)[::-1]  # highest score first

    labels = ["Champion", "Loyal", "At Risk", "Lost"]
    return {int(cluster_id): label for cluster_id, label in zip(ranked, labels)}


# ── Training ───────────────────────────────────────────────────────────────────

def train_rfm_model(cursor) -> dict:
    """
    Compute RFM for all B2C customers and train K-Means (k=4).
    Saves model + label_map to admin_rfm_model.pkl.
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import MinMaxScaler

    cursor.execute("""
        SELECT
            u.Id,
            DATEDIFF(day, MAX(co.CreatedAt), GETDATE())  AS recency_days,
            COUNT(co.Id)                                  AS frequency,
            ISNULL(SUM(co.TotalAmount), 0)                AS monetary
        FROM AspNetUsers u
        JOIN AspNetUserRoles ur ON ur.UserId = u.Id
        JOIN AspNetRoles r ON r.Id = ur.RoleId
        JOIN CustomerOrders co
            ON co.CustomerId = u.Id AND co.Status != 5
        WHERE r.Name = 'Customer'
        GROUP BY u.Id
        HAVING COUNT(co.Id) > 0
    """)
    rows = cursor.fetchall()

    if len(rows) < 4:
        return {
            "status": "skipped",
            "reason": f"Need >= 4 customers with orders for K-Means (found {len(rows)})",
            "fallback": "rule-based segmentation used at inference time",
        }

    ids = [r[0] for r in rows]
    X   = np.array([[float(r[1]), float(r[2]), float(r[3])] for r in rows])

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    k = min(4, len(rows))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X_scaled)

    label_map = _map_clusters_to_labels(km.cluster_centers_)

    bundle = {
        "model":       km,
        "scaler":      scaler,
        "label_map":   label_map,
        "trained_at":  datetime.utcnow().isoformat(),
        "n_customers": len(rows),
        "k":           k,
    }

    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(RFM_MODEL_PATH, "wb") as f:
        pickle.dump(bundle, f)

    return {
        "status":      "trained",
        "n_customers": len(rows),
        "k_clusters":  k,
        "label_map":   label_map,
        "trained_at":  bundle["trained_at"],
    }


# ── Inference & Write-back ────────────────────────────────────────────────────

def segment_all_customers(cursor) -> dict:
    """
    Assign RFM segment to every B2C customer.
    Writes segment label to AspNetUsers.RfmSegment.
    Returns segment distribution summary.
    """
    # Compute RFM scores
    cursor.execute("""
        SELECT
            u.Id,
            DATEDIFF(day, MAX(co.CreatedAt), GETDATE())  AS recency_days,
            COUNT(co.Id)                                  AS frequency,
            ISNULL(SUM(co.TotalAmount), 0)                AS monetary
        FROM AspNetUsers u
        JOIN AspNetUserRoles ur ON ur.UserId = u.Id
        JOIN AspNetRoles r ON r.Id = ur.RoleId
        JOIN CustomerOrders co
            ON co.CustomerId = u.Id AND co.Status != 5
        WHERE r.Name = 'Customer'
        GROUP BY u.Id
        HAVING COUNT(co.Id) > 0
    """)
    rows = cursor.fetchall()
    if not rows:
        return {"status": "no_customers", "segments": {}}

    ids = [r[0] for r in rows]
    rfm = [(float(r[1]), float(r[2]), float(r[3])) for r in rows]

    # Predict using trained model or fall back to rules
    segments = {}
    if os.path.exists(RFM_MODEL_PATH):
        try:
            with open(RFM_MODEL_PATH, "rb") as f:
                bundle = pickle.load(f)
            model     = bundle["model"]
            scaler    = bundle["scaler"]
            label_map = bundle["label_map"]
            X_scaled  = scaler.transform(np.array(rfm))
            cluster_ids = model.predict(X_scaled)
            for uid, cid in zip(ids, cluster_ids):
                segments[uid] = label_map.get(int(cid), "Loyal")
        except Exception:
            for uid, (r, f, m) in zip(ids, rfm):
                segments[uid] = _rule_based_segment(r, int(f), m)
    else:
        for uid, (r, f, m) in zip(ids, rfm):
            segments[uid] = _rule_based_segment(r, int(f), m)

    # Write back to DB (requires AspNetUsers.RfmSegment column)
    written = 0
    skipped = 0
    for uid, label in segments.items():
        try:
            cursor.execute(
                "UPDATE AspNetUsers SET RfmSegment = ? WHERE Id = ?",
                (label, uid)
            )
            written += 1
        except Exception:
            skipped += 1  # Column may not exist yet — skip silently

    # Distribution summary
    distribution: dict = {}
    for label in segments.values():
        distribution[label] = distribution.get(label, 0) + 1

    return {
        "status":       "complete",
        "total":        len(segments),
        "written_to_db":written,
        "skipped":      skipped,
        "distribution": distribution,
    }


def get_rfm_segments(cursor) -> dict:
    """
    Return current RFM segment distribution (read from DB if column exists,
    otherwise compute on the fly without writing back).
    """
    # Try reading from DB first
    try:
        cursor.execute("""
            SELECT RfmSegment, COUNT(*) AS cnt
            FROM AspNetUsers u
            JOIN AspNetUserRoles ur ON ur.UserId = u.Id
            JOIN AspNetRoles r ON r.Id = ur.RoleId
            WHERE r.Name = 'Customer'
              AND RfmSegment IS NOT NULL
            GROUP BY RfmSegment
        """)
        db_rows = cursor.fetchall()
        if db_rows:
            distribution = {r[0]: r[1] for r in db_rows}
            return {
                "source":       "database",
                "distribution": distribution,
                "total":        sum(distribution.values()),
            }
    except Exception:
        pass  # Column doesn't exist yet

    # Fall back: compute without writing
    result = segment_all_customers(cursor)
    return {
        "source":       "computed",
        "distribution": result.get("distribution", {}),
        "total":        result.get("total", 0),
    }
