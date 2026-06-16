# Talentree AI Service — Azure Deployment Guide

This guide walks you through deploying the **Talentree AI** microservice (FastAPI + Docker) to **Microsoft Azure** using continuous deployment with your **GitHub** account.

We will use **Azure Container Apps (ACA)**, which is a serverless container hosting service. It is highly cost-effective, handles scaling (including scaling to 0 when there is no traffic), and integrates directly with GitHub to set up your build pipeline.

---

## Prerequisites
1. An active **Azure Subscription** (e.g. Free, Pay-As-You-Go, etc.).
2. A **GitHub Account** with access to the repository: `https://github.com/Talentree-Platform/AI_Repo.git`.
3. The database connection credentials (listed below in Step 4).

---

## Step 1: Create an Azure Container App

1. Log into the [Azure Portal](https://portal.azure.com/).
2. In the search bar at the top, search for **Container Apps** and select it.
3. Click **Create** (or **Create container app**).
4. Fill in the **Basics** tab:
   - **Subscription**: Select your Azure subscription.
   - **Resource Group**: Click *Create new* if you don't have one (e.g., `rg-talentree-prod`).
   - **Container app name**: Enter `talentree-ai-service`.
   - **Region**: Choose a region near your users (e.g., `East US` or `North Europe`).
   - **Workload profile**: Select **Consumption** (Serverless, cheap, scales to 0).
   - **Container Apps Environment**: Click *Create new* to set up the environment with default settings.

---

## Step 2: Configure Continuous Deployment via GitHub

Instead of configuring Docker registry logins manually, we will let Azure configure GitHub Actions for us.

1. Move to the **Container** tab or click **Next: Container >**.
2. Uncheck **Use quickstart image** if it is checked.
3. In the **Deployment source** configuration:
   - Select **GitHub**.
   - Click **Authorize** (if prompted) to sign into your GitHub account and grant Azure permission to read and write to your repositories.
4. Under **GitHub Repository Details**:
   - **Organization**: Select `Talentree-Platform`.
   - **Repository**: Select `AI_Repo`.
   - **Branch**: Select `feature/bo-dashboard` (or `main` when ready).
5. Under **Build Configuration**:
   - **Build Type**: Select **Dockerfile**.
   - **Dockerfile Path**: Enter `Dockerfile` (or `talentree-ai/Dockerfile` since the Dockerfile is inside the subdirectory of your workspace).
     > [!IMPORTANT]
     > Since the repository has the FastAPI service inside the `talentree-ai` subdirectory, configure the paths as follows:
     > - **Context Path**: `talentree-ai` (This points to the folder containing the project files)
     > - **Dockerfile Path**: `Dockerfile` (Relative to the context path)
6. Under **Target Port**:
   - Enter **`7860`** (FastAPI runs on port `7860` as configured in the `Dockerfile`).

---

## Step 3: Configure Ingress (Public Web Access)

To make your API accessible over the internet:

1. In the **Ingress** tab (or search configuration):
   - Check **Enabled**.
   - **Traffic**: Select **Accepting traffic from anywhere (External)**.
   - **Target Port**: Ensure it is set to **`7860`**.
   - **Transport**: Select **Auto** or **HTTP/1.1**.

Click **Review + Create**, then click **Create**. Azure will now start provisioning the resource, which takes 2–4 minutes.

> [!NOTE]
> Azure will automatically create an **Azure Container Registry (ACR)** for you, register a Service Principal, create repository secrets on GitHub, and commit a GitHub Actions workflow file (e.g. `.github/workflows/azure-container-apps-....yml`) directly to your branch. This workflow will automatically trigger to build and deploy your container.

---

## Step 4: Configure Database Environment Variables

Once the Container App is successfully created, you must add the SQL database connection strings to the app's configuration so it can read and write data.

1. In the Azure Portal, navigate to your newly created **Container App** (`talentree-ai-service`).
2. Under the **Settings** menu on the left sidebar, click **Configuration** (or **Containers** -> **Edit and deploy**).
3. Under the **Environment Variables** section, add the following variables:

| Environment Variable | Value |
| :--- | :--- |
| `DB_SERVER` | `db52715.public.databaseasp.net` |
| `DB_NAME` | `db52715` |
| `DB_USER` | `db52715` |
| `DB_PASSWORD` | `Kg4+5#hGcH=8` |

4. Click **Save** or **Create New Revision** to apply the changes. The container will automatically restart and connect to the database.

---

## Step 5: Verify Deployment

1. On the Container App's **Overview** page, find the **Application Url** (e.g., `https://talentree-ai-service.xxxxxx.azurecontainerapps.io`).
2. Open this URL in your browser:
   - To check the service status, visit: `/ai/status` (It should return `{"status": "ok", "database": "connected"}`).
   - To view the interactive API documentation, visit: `/docs`.

---

## Troubleshooting & FAQ

### 1. Where do I see build logs?
In your GitHub repository under the **Actions** tab, you will see a new workflow running called something like *Trigger deployment for talentree-ai-service*. You can click on it to see the build and push logs.

### 2. Can I manually write the GitHub Action workflow?
Yes. If you prefer to manage the workflow yourself rather than letting Azure auto-generate it, you can place this template in `.github/workflows/azure-deploy.yml`:

```yaml
name: Build and Deploy to Azure Container Apps

on:
  push:
    branches:
      - feature/bo-dashboard

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Log in to Azure
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and Deploy to ACA
        uses: azure/container-apps-deploy-action@v2
        with:
          appSource: ${{ github.workspace }}/talentree-ai
          registryUrl: ${{ secrets.AZURE_REGISTRY_URL }}
          registryUsername: ${{ secrets.AZURE_REGISTRY_USERNAME }}
          registryPassword: ${{ secrets.AZURE_REGISTRY_PASSWORD }}
          containerAppName: talentree-ai-service
          resourceGroup: rg-talentree-prod
          imageToBuild: ${{ secrets.AZURE_REGISTRY_URL }}/talentree-ai:${{ github.sha }}
```
*Note: This requires setting up the Secrets `AZURE_CREDENTIALS`, `AZURE_REGISTRY_URL`, `AZURE_REGISTRY_USERNAME`, `AZURE_REGISTRY_PASSWORD` in your GitHub repository manually.*
