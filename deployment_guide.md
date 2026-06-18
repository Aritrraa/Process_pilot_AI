# ProcessPilot AI — Free Cloud Deployment Guide

This guide outlines a step-by-step, **100% free-of-cost** pipeline to deploy the ProcessPilot AI full-stack application to the cloud.

---

## 🏗️ Architecture & Free-Tier Services

To run this platform in production, we will split the services across the following free-tier cloud providers:

```
[React Frontend] (Vercel)
       │
       ▼ (REST API Calls)
[FastAPI Backend] (Render / Koyeb)
  ├──► [Relational DB] (Neon Serverless PostgreSQL)
  └──► [Vector Store] (Pinecone / Qdrant Cloud)
```

| Component | Cloud Service | Free Tier Allowances |
| :--- | :--- | :--- |
| **Frontend Web Console** | **Vercel** | Free hosting for hobby projects, unlimited bandwidth, auto-git builds |
| **Backend API Server** | **Render** (or **Koyeb**) | Render: Free web service (switches to sleep mode after 15 min inactivity)<br>Koyeb: Free instance (512MB RAM, always active) |
| **Relational Database** | **Neon** | 1 Serverless Postgres project, 0.5 GB storage, auto-suspend |
| **Vector DB (Embeddings)**| **Pinecone** | 1 Starter Index (up to 2M vectors), free standard console |

---

## 📡 Part 1: Relational Database Setup (Neon PostgreSQL)

We will set up a serverless PostgreSQL database to replace the local development SQLite file.

1. Go to [Neon.tech](https://neon.tech/) and sign up for a free account.
2. Create a new project:
   * **Project Name**: `processpilot-db`
   * **Postgres Version**: Keep default (e.g. 15 or 16)
   * **Cloud Provider & Region**: Select the region closest to you (or select US East to match Render's default servers).
3. Once created, copy the **Connection String** displayed on the dashboard. It will look like this:
   ```text
   postgresql://aritrraa:<password>@ep-weathered-wind-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Save this string; this is your production `DATABASE_URL`.

---

## 🌲 Part 2: Vector Database Setup (Pinecone)

Since local ChromaDB files are ephemeral and get wiped out on free hosting servers when instances restart, we will use our built-in Pinecone adapter.

1. Go to [Pinecone.io](https://www.pinecone.io/) and register for a free account.
2. Navigate to **API Keys** on the sidebar and copy your default API key. This is your `PINECONE_API_KEY`.
3. Go to **Indexes** and click **Create Index**:
   * **Index Name**: `processpilot` (must match the config env `PINECONE_INDEX` default)
   * **Dimensions**: `768` (must match Gemini's `text-embedding-004` dimensions)
   * **Metric**: `cosine`
   * **Select Pod type**: Serverless
   * **Cloud Provider / Region**: AWS us-east-1 (or matching regional free tier)
4. Copy the environment variables:
   * `PINECONE_API_KEY`
   * `PINECONE_INDEX` (value: `processpilot`)
   * `VECTOR_DB_TYPE` (value: `pinecone`)

---

## 🐍 Part 3: Backend API Server Deployment (Render)

Render provides direct GitHub integrations and builds your project automatically on push.

1. Go to [Render.com](https://render.com/) and log in (sign up via GitHub is recommended).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository: `Aritrraa/Process_pilot_AI`.
4. Configure the Web Service settings:
   * **Name**: `processpilot-backend`
   * **Language**: `Python`
   * **Branch**: `main`
   * **Region**: Oregon (US West) or Frankfurt (EU Central)
   * **Root Directory**: `backend` (⚠️ *Very Important: must point to backend folder*)
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `python run.py` (which runs Uvicorn on host `0.0.0.0` and port `8000`)
5. Scroll down to **Instance Type** and select the **Free** tier.
6. Click **Advanced** and add the following **Environment Variables**:

| Key | Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | *Your Neon PostgreSQL connection string* | Swaps database driver to PostgreSQL |
| `VECTOR_DB_TYPE` | `pinecone` | Swaps vector search from Chroma to Pinecone |
| `PINECONE_API_KEY` | *Your Pinecone API Key* | Authenticates Pinecone client |
| `PINECONE_INDEX` | `processpilot` | Target index name |
| `SECRET_KEY` | *A random long string, e.g. `prod_secret_pilot_ai_hash`* | Secures authentication tokens |
| `BACKEND_CORS_ORIGINS` | `https://your-frontend.vercel.app` | *Leave blank initially*, then update once your Vercel URL is generated |

7. Click **Create Web Service**. Render will install requirements, create database schemas automatically via Alembic on run, and start the API.
8. Once deployed, copy the Render service URL (e.g. `https://processpilot-backend.onrender.com`). This is your `VITE_API_URL`.

---

## ⚛️ Part 4: Frontend Web Deployment (Vercel)

Vercel is the premier free platform for hosting React single-page applications.

1. Go to [Vercel.com](https://vercel.com/) and log in using your GitHub account.
2. Click **Add New** -> **Project**.
3. Import your GitHub repository: `Aritrraa/Process_pilot_AI`.
4. Configure the Project settings:
   * **Framework Preset**: `Vite`
   * **Root Directory**: `frontend` (⚠️ *Very Important: must point to frontend folder*)
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
5. Expand the **Environment Variables** section and add:
   * **Key**: `VITE_API_URL`
   * **Value**: *Your Render backend URL* (e.g., `https://processpilot-backend.onrender.com/api/v1`)
6. Click **Deploy**. Vercel will build your static React assets and generate a public link (e.g., `https://processpilot-ai.vercel.app`).

---

## 🔗 Part 5: Final CORS Handshake

To allow security clearance between your Vercel frontend and Render backend:
1. Go to your backend page on **Render.com**.
2. Navigate to **Environment**.
3. Update the variable `BACKEND_CORS_ORIGINS` with your new Vercel frontend URL (e.g., `https://processpilot-ai.vercel.app`).
4. Save changes. Render will automatically redeploy the backend with the new CORS permissions.

---

## ⚡ Part 6: Seeding Your Cloud Database

To populate your live Neon database with the complete enterprise dataset (Sarah, John, tasks, and files):
1. Open a local terminal in your project's `/backend` directory.
2. Temporarily set your environment variable to point to the Neon database:
   ```powershell
   # Windows PowerShell:
   $env:DATABASE_URL="your_neon_connection_string"
   $env:VECTOR_DB_TYPE="pinecone"
   $env:PINECONE_API_KEY="your_pinecone_api_key"
   $env:PINECONE_INDEX="processpilot"
   ```
3. Run the database migrations locally to build the tables in Neon:
   ```bash
   alembic upgrade head
   ```
4. Run the seed script to write the mock organizational directories:
   ```bash
   python seed_demo.py
   ```
5. Your cloud database is now seeded! You can now log into your live Vercel site using the standard demo credentials.
