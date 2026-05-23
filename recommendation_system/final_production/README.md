# Enterprise Recommendation System Portal

A production-grade, highly-decoupled, end-to-end recommendation system simulating a real enterprise AI environment. This system manages two completely independent pipelines serving B2C customer products and B2B business owner procurement planning.

---

## 🌟 Key Architectural Principles

1. **Decoupled Feature Layer**: The machine learning recommendation logic is schema-independent. It does not couple directly to standard transaction databases. Feature tables/flat files serve as the intermediary layer, preparing the system for safe integrations with Azure SQL, MonsterASP, or any custom business database schemas.
2. **APIs and Pipelines Isolation**: Customer Product personalization and Business Owner inventory planning are treated as separate internal microservices. They run on independent pipelines, models, evaluations, logging mechanisms, and MLflow experiment runs.
3. **Continuous Hot-Reload retraining**: Online retraining runs in background tasks, keeping high-performance API serving fully uninterrupted. Models are promoted only after passing validation metric gating checks (new candidate vs active production model).

---

## 📂 Project Structure

```
final_production/
│
├── customer_recommender/      # Customer System B2C microservice
│   ├── api/                   # FastAPI routes & Pydantic request/response schemas
│   ├── model/                 # Hybrid Content-Based + Item-Item Collaborative Model
│   ├── training/              # Offline model training pipeline
│   ├── retraining/            # Gated online retraining trigger
│   ├── evaluation/            # Custom Precision@K, Recall@K, NDCG implementations
│   ├── services/              # High-level model wrapper and reload service
│   ├── templates/             # Dashboard HTML
│   └── static/                # Static CSS / JS assets
│
├── owner_recommender/         # Business Owner System B2B microservice
│   ├── api/                   # FastAPI routes & Pydantic schemas
│   ├── model/                 # Procurement Scoring and Ridge Demand Forecaster
│   ├── training/              # Offline training pipeline
│   ├── retraining/            # Gated online retraining trigger
│   ├── evaluation/            # Demand Forecasting RMSE/MAE & Procurement Precision@K
│   ├── services/              # High-level model wrapper and reload service
│   ├── templates/             # Dashboard HTML
│   └── static/                # Static CSS / JS assets
│
├── shared/                    # Shared infrastructure modules
│   ├── database/              # SQLAlchemy connection pools & interaction schema models
│   ├── config/                # Environment configuration parsing via Pydantic
│   ├── utils/                 # rotating file loggers
│   └── common_models/         # Shared models
│
├── scripts/                   # Utility Scripts
│   ├── generate_data.py       # Generates 100,000 seasonal, cyclic interactions
│   ├── seed_customer_data.py  # Seeds customer records into SQL Server
│   └── seed_owner_data.py     # Seeds owner records into SQL Server
│
├── trained_models/            # Version-controlled joblib files
│   ├── customer/              # customer/v1/ and customer/latest/
│   └── owner/                 # owner/v1/ and owner/latest/
│
├── data/                      # Local JSON dataset cache
├── logs/                      # Service runtime logs
├── requirements.txt           # Python application dependencies
├── Dockerfile                 # Slim FreeTDS compiled application container
├── docker-compose.yml         # Container stack: SQL Server, MLflow server, FastAPI serving
├── .env.example               # Template environment configuration
├── main.py                    # Unified service entrypoint
└── README.md                  # System instruction handbook
```

---

## 🛠️ Database Schema

We define a central interaction log matching standard transactional tables:

```sql
CREATE TABLE interactions (
    interaction_id INT PRIMARY KEY IDENTITY(1,1),
    user_type VARCHAR(20),                -- 'customer' or 'owner'
    user_id INT,
    item_id INT,
    item_type VARCHAR(20),                -- 'product' or 'raw_material'
    interaction_type VARCHAR(50),         -- 'view', 'purchase', 'reorder', 'click'
    category VARCHAR(100),
    quantity INT,
    price FLOAT,
    interaction_timestamp DATETIME DEFAULT GETDATE()
);
```

---

## 🖥️ Local Installation and Setup

### 1. Requirements
Ensure you have the following installed locally:
- Python 3.11
- Docker & Docker Compose
- FreeTDS (required for standard `pymssql` compilation if building from source)

### 2. Generate Synthetic Data
Run the generator to create the 100,000 highly-realistic interactions, complete with weekend purchase seasonality and cyclical business reorder patterns:
```bash
python scripts/generate_data.py
```
This writes four files:
- `data/products.json`
- `data/raw_materials.json`
- `data/customer_interactions.json`
- `data/owner_interactions.json`

### 3. Run Offline Initial Model Training
Compile and run the initial models. This fits the content representations, computes similarity matrices, configures the forecasting Ridge regressor, and outputs `joblib` files locally:
```bash
# Train Customer Product System
python customer_recommender/training/train.py

# Train Owner Raw Material System
python owner_recommender/training/train.py
```

### 4. Run the Full Stack via Docker Compose
Build and boot the SQL Server, MLflow Server, and FastAPI serving layers simultaneously:
```bash
docker-compose up --build
```
Once healthy, access these services at:
*   **FastAPI Portal Gate**: [http://localhost:8000](http://localhost:8000)
*   **Customer Personalization Dashboard**: [http://localhost:8000/customer-ui](http://localhost:8000/customer-ui)
*   **Owner Procurement Dashboard**: [http://localhost:8000/owner-ui](http://localhost:8000/owner-ui)
*   **MLflow Experiment UI**: [http://localhost:5000](http://localhost:5000)

### 5. Seed SQL Server (Optional Database Synchronization)
Once the database container is healthy, populate it using our seeding pipelines (leveraging bulk SQLAlchemy inserts):
```bash
# Seed customer database entries
python scripts/seed_customer_data.py

# Seed owner procurement database entries
python scripts/seed_owner_data.py
```

---

## 🌐 FastAPI Route Documentation

### Customer Endpoints
*   `GET /customer/health`
    *   **Description**: Verification of service availability and active model states.
*   `POST /customer/recommend`
    *   **Payload**: `{ "customer_id": 123, "top_k": 5 }`
    *   **Description**: Computes hybrid weighted user-item collaborative content recommendation list.
*   `POST /customer/retrain`
    *   **Description**: Non-blocking async online retraining, writing metrics to MLflow.
*   `GET /customer/model-info`
    *   **Description**: Active parameters, modification times, and metrics.

### Owner Endpoints
*   `GET /owner/health`
    *   **Description**: Verification of service availability and active model states.
*   `POST /owner/recommend`
    *   **Payload**: `{ "owner_id": 55, "top_k": 5 }`
    *   **Description**: Scores raw materials by combining procurement volumes, reorder urgency ratios, and predicted Ridge demand.
*   `POST /owner/retrain`
    *   **Description**: Non-blocking async online retraining, writing metrics to MLflow.
*   `GET /owner/model-info`
    *   **Description**: Parameters and metrics.

---

## ☁️ Azure VM Production Deployment Guide

Deploying this stack on an Azure Ubuntu VM is simple, robust, and enterprise-ready.

### 1. Provision Azure VM
1. Go to the **Azure Portal** and create a new **Virtual Machine**.
2. Select **Ubuntu Server 20.04 LTS / 22.04 LTS** as the Operating System.
3. Size: `Standard_B2s` (2 vCPUs, 4 GiB memory) is ideal for testing; use `Standard_D2s_v5` for production.
4. Under **Inbound Port Rules**, open ports:
   *   `22` (SSH)
   *   `80` (HTTP) and `443` (HTTPS)
   *   `8000` (FastAPI serve)
   *   `5000` (MLflow Tracking)
5. Generate/use SSH Keys to authenticate.

### 2. Connect and Prepare Environment
SSH into your Azure VM:
```bash
ssh -i /path/to/your/key.pem azureuser@<VM-PUBLIC-IP>
```

Update system files:
```bash
sudo apt-get update && sudo apt-get upgrade -y
```

### 3. Install Docker & Docker Compose
Install the Docker engine:
```bash
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Allow running docker without sudo (re-login required after this)
sudo usermod -aG docker $USER
```

Install Docker Compose:
```bash
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 4. Clone and Build Codebase
1. SCP or Git Clone your code onto the VM.
2. Navigate into the cloned folder containing `docker-compose.yml`.
3. Create `.env` from `.env.example`, adjusting host values:
   ```bash
   cp .env.example .env
   # Update DB_HOST to 'sqlserver' inside the docker network
   sed -i 's/DB_HOST="localhost"/DB_HOST="sqlserver"/g' .env
   ```
4. Build and boot the microservices:
   ```bash
   docker-compose up --build -d
   ```

### 5. Setup Weekly Automatic Retraining via Crontab
To perform automatic weekly retraining at Sunday midnight, configure standard Linux cron schedules.

Create a retraining script on the VM host (`/home/azureuser/trigger_retrain.sh`):
```bash
#!/bin/bash
# Move to codebase directory
cd /home/azureuser/recommendation_system

# Trigger retraining inside the running FastAPI app container
docker exec -d recommendation_app python -c "
from customer_recommender.retraining.pipeline import run_retraining_pipeline
from owner_recommender.retraining.pipeline import run_owner_retraining_pipeline
print('Customer Retrain Status:', run_retraining_pipeline())
print('Owner Retrain Status:', run_owner_retraining_pipeline())
" >> /home/azureuser/logs/cron_retrain.log 2>&1
```

Make it executable:
```bash
chmod +x /home/azureuser/trigger_retrain.sh
mkdir -p /home/azureuser/logs
```

Add the crontab schedule:
```bash
# Open crontab config
crontab -e

# Insert this line at the bottom to trigger every Sunday at midnight (00:00)
0 0 * * 0 /home/azureuser/trigger_retrain.sh
```

---

## 📈 Monitoring & Experiments Tracking
Both models compile metrics (Precision@K, NDCG, RMSE) into separate MLflow experiments:
*   `customer_recommender_experiment`
*   `owner_recommender_experiment`

The FastAPI server records modular Rotating File logs under `logs/api.log`, `customer_recommender/logs/customer.log`, and `owner_recommender/logs/owner.log`. Ensure to track these files on Azure VM for active production monitoring.
