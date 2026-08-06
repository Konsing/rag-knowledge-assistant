# Public Showcase Deployment

This guide deploys the personal, non-commercial showcase with services that currently have a $0 plan:

- Vercel Hobby: static React/Vite frontend
- Render Free: slim FastAPI container
- Qdrant Cloud Free: persistent vector database and free cloud embeddings
- hCaptcha Basic: bot challenge

OpenAI or Anthropic generation is not free. Use a dedicated project API key, set the smallest practical provider-side usage limits and alerts, and keep the demo's daily limit conservative. Confirm whether your provider's budget is a hard stop or only an alert. No provider promises that a free plan will exist forever; review their terms before each interview cycle.

## Current deployment

- Public showcase: [https://rag-knowledge-assistant-puce.vercel.app](https://rag-knowledge-assistant-puce.vercel.app/)
- API health: [https://rag-showcase-api.onrender.com/api/health](https://rag-showcase-api.onrender.com/api/health)

The public frontend URL is also configured as the GitHub repository homepage. The API can cold-start after inactivity; a temporary loading message during the first request is expected.

## What the public can do

- List the curated documents.
- Inspect stored chunk text and citation metadata.
- Select up to five documents as the retrieval scope.
- Ask a bounded question after bot verification.
- Inspect the retrieved chunks, similarity scores, model, latency, citations, and cache status.

The public cannot upload documents, seed the corpus, access the Qdrant key, invoke the MCP server, or obtain the LLM/admin credentials.

## Where `DEMO_MODE=true` goes

`DEMO_MODE` is a backend environment variable; it is not a toggle in the website or Qdrant.

- **Local Docker:** create the repository-root `.env` from `.env.example`, then change `DEMO_MODE=false` to `DEMO_MODE=true`. The `.env` file is ignored by Git.
- **Render:** no manual change is needed. The root `render.yaml` already declares `DEMO_MODE` as `"true"` for the hosted API.
- **Vercel:** do not add `DEMO_MODE`. Vercel only hosts the frontend; the frontend reads `/api/demo/config` from Render and adapts automatically.

For a local showcase, the minimum relevant `.env` settings are:

```env
DEMO_MODE=true
DEMO_AUTO_SEED=true
ADMIN_API_KEY=replace-with-a-long-random-value
EMBEDDING_PROVIDER=local
```

Leave `DEMO_MODE=false` for the original local upload-and-query interface.

## 1. Create Qdrant Cloud Free

### 1.1 Create the cluster

1. Open the [Qdrant Cloud Console](https://cloud.qdrant.io/) and choose **Clusters**.
2. Click **Create**, **Create cluster**, or **Create Free Cluster**; the wording can vary slightly with the console layout.
3. Select the **Free** cluster type. Confirm that the price summary is `$0` before creating it.
4. Use this cluster name:

   ```text
   rag-showcase
   ```

   The name is only a label in your dashboard and does not have to match the Qdrant collection or Render service. Renaming it later does not change its endpoint.
5. Choose any provider offered by the Free tier. There is no project-specific AWS/GCP/Azure requirement.
6. Choose an available **US region**, preferably the closest one to the US West Coast. This keeps it reasonably close to a Render service in Oregon and ensures access to Qdrant's US-hosted free inference models. If only one free region is offered, use it.
7. Leave the Free tier's CPU, RAM, disk, and single-node settings unchanged. The curated corpus is tiny compared with the free cluster capacity.
8. Create the cluster and wait until its status is healthy/green. Provisioning may take several minutes.

Do **not** manually create a collection. When the Render API starts, this project automatically creates a collection named `research_papers` with 384-dimensional cosine vectors and the required `doc_id` index.

### 1.2 Find Cloud Inference

Cloud Inference is not shown on the account overview or initial cluster-creation form. Open **Clusters → rag-showcase**, then look for an **Inference** tab on that cluster's detail page.

Qdrant states that inference is enabled by default for clusters created after July 7, 2025. Because this is a new cluster, there may be no separate enable switch. In the **Inference** tab, locate:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Confirm that it has a **Cost: Free** label. Do not select a similarly named paid model or configure an external OpenAI embedding provider; the application is already configured to request this exact free model.

If you still cannot see **Inference**:

1. Confirm the cluster has finished provisioning and that you opened the cluster detail page rather than the account dashboard.
2. Refresh the console or sign out and back in after the cluster becomes healthy.
3. Confirm this is a **Qdrant Managed Cloud** cluster, not a self-hosted/Hybrid Cloud cluster.
4. Look under the cluster's **Configuration** or overflow menu in case the console moved the tab.
5. Continue creating the database key below. The definitive test is the initial seed from Render; if it reports that cloud inference is disabled and no console control exists, use Qdrant's support link from the console.

### 1.3 Create the database API key

Qdrant may offer a database key immediately after cluster creation. Copy it then because it is only displayed once. If you dismissed that screen:

1. Open **Clusters → rag-showcase → API Keys**.
2. Click **Create**.
3. Name it:

   ```text
   rag-showcase-render
   ```

4. Choose cluster-wide **Manage/Write** permission, not read-only. The backend must create the collection and index, seed points, search them, and update the daily usage counter.
5. For the simplest interview demo, leave expiration empty if the console permits it, then rotate the key manually. If you choose an expiration, create a calendar reminder and update Render before it expires.
6. Create the key, copy it immediately, and store it in your password manager as `QDRANT_API_KEY`. Never paste it into Git, Vercel, screenshots, or this chat.

This is a **Database API key**, not a Cloud Management key. The application does not need permission to create or delete Qdrant Cloud clusters.

### 1.4 Copy and test the cluster endpoint

On the `rag-showcase` cluster's **Overview** page, copy the main HTTPS cluster endpoint. It resembles:

```text
https://YOUR-CLUSTER-ID.REGION.PROVIDER.cloud.qdrant.io:6333
```

Save the exact value as `QDRANT_URL`. Use the main/load-balanced cluster endpoint—not the browser dashboard URL, the Cloud Management API, or a node-specific endpoint.

Test it locally with placeholders replaced only in your own terminal. Paste the complete endpoint exactly once: if the copied value already begins with `https://`, do not add another `https://` and do not leave placeholder text or angle brackets in the command.

```bash
curl --fail --show-error \
  --header "api-key: YOUR_QDRANT_DATABASE_API_KEY" \
  "YOUR_COMPLETE_QDRANT_URL"
```

For example, the final URL argument should have this shape:

```text
"https://abc123.us-west.example.cloud.qdrant.io:6333"
```

It must not look like any of these malformed forms:

```text
"https://https://abc123..."
"QDRANT_URL=https://abc123..."
"<https://abc123...>"
"https://abc123...:6333:6333"
```

For Bash, this interactive version keeps the API key out of shell history and avoids editing a long command:

```bash
read -r -p "Qdrant URL: " QDRANT_TEST_URL
read -r -s -p "Qdrant database API key: " QDRANT_TEST_KEY
echo
curl --fail --show-error \
  --header "api-key: ${QDRANT_TEST_KEY}" \
  "${QDRANT_TEST_URL}"
unset QDRANT_TEST_KEY QDRANT_TEST_URL
```

A successful response contains Qdrant's title and version. `401` means the key is wrong; a DNS/connection error usually means the endpoint was copied incorrectly or the cluster is not ready.

At the end of this step, you should have exactly two values ready for Render:

```text
QDRANT_URL=https://...cloud.qdrant.io:6333
QDRANT_API_KEY=the-secret-database-key-shown-once
```

The free cluster is enough for this tiny corpus, but Qdrant currently suspends inactive free clusters and can delete them after extended inactivity. Visit the console before an interview if the demo has been unused for several weeks. The corpus manifest makes re-seeding deterministic after recreating a cluster.

Do not put the Qdrant key in Vercel. Only FastAPI should connect to Qdrant.

## 2. Create hCaptcha Basic

You can do this before Vercel assigns a hostname. Start without a domain allowlist, then restrict the sitekey after the Vercel deployment.

1. Sign in to the [hCaptcha Dashboard](https://dashboard.hcaptcha.com/) on the free Basic plan.
2. Open **Sites** and create a sitekey named `rag-showcase`.
3. Keep the default Basic challenge behavior. Copy the site's public **Sitekey** and save it as `HCAPTCHA_SITE_KEY`.
4. Open your profile/settings page and find or generate the account **Secret** used by Siteverify. Copy it once and save it as `HCAPTCHA_SECRET`.
5. If the dashboard offers domain allowlisting, leave it disabled temporarily. After Vercel gives you a production hostname, enable it and add only the bare hostname, for example:

   ```text
   rag-knowledge-assistant.vercel.app
   ```

   Do not include `https://`, a path, or a trailing slash.

The site key is intentionally returned to the browser. The secret must exist only in Render. The backend submits the token, visitor IP, and expected sitekey to hCaptcha before processing a demo query.

Do not add `localhost` or `127.0.0.1` to hCaptcha: hCaptcha's documentation says those hostnames are prohibited. For local showcase testing, leave both hCaptcha variables empty as shown later in this guide; the production Render deployment should have both values.

## 3. Deploy the Render backend

### 3.1 Make sure Render can see the deployment files

Render builds from GitHub, not from your uncommitted local working tree. Commit and push the showcase changes before creating the Blueprint. The repository's default branch must contain:

```text
render.yaml
backend/Dockerfile.demo
backend/requirements-demo.txt
backend/demo_documents.json
```

Do not commit `.env` or any real credentials.

### 3.2 Create the Blueprint

1. Sign in to [Render](https://dashboard.render.com/) using GitHub.
2. Choose **New → Blueprint**.
3. Connect/authorize the GitHub repository `rag-knowledge-assistant`.
4. Use the repository's default production branch, normally `main`.
5. Render should find `/render.yaml` automatically. If it asks for a path, enter:

   ```text
   render.yaml
   ```

6. Name the Blueprint `rag-showcase` if prompted.
7. Review the proposed service before applying it. It should show:

   ```text
   Service: rag-showcase-api
   Type: Web Service / Docker
   Plan: Free
   Region: Oregon
   Health check: /api/health
   ```

8. Supply each environment variable marked `sync: false`:

   - `QDRANT_URL`: the HTTPS Qdrant cluster URL
   - `QDRANT_API_KEY`: the Qdrant **Database** API key with manage/write access
   - `OPENAI_API_KEY`: a dedicated demo project key, preferably not your general-purpose key
   - `HCAPTCHA_SITE_KEY`: the public hCaptcha site key
   - `HCAPTCHA_SECRET`: the private hCaptcha secret
   - `CORS_ORIGINS`: initially use `https://placeholder.invalid`; replace it with the final Vercel origin in step 4

   Do not add quotes around dashboard values and do not paste the `KEY=value` form into a value field—paste only the value.
9. Apply/create the Blueprint. Render will build `backend/Dockerfile.demo`; the first build can take several minutes.
10. Open **rag-showcase-api → Environment**. Confirm these values were supplied by `render.yaml`:

    ```text
    DEMO_MODE=true
    DEMO_AUTO_SEED=true
    EMBEDDING_PROVIDER=qdrant_cloud
    EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
    QDRANT_CLOUD_INFERENCE=true
    DEMO_QUERIES_PER_HOUR=10
    DEMO_QUERIES_PER_DAY=50
    ```

11. Render generates `ADMIN_API_KEY`. Reveal/copy it from the service environment page and store it in your password manager. If the dashboard does not allow you to retrieve the generated value, replace it with your own long random value and choose **Save and deploy**.
12. Open **Logs**. A successful startup should show Uvicorn listening on Render's assigned port. The background corpus seed may continue for several minutes.
13. Copy the public service URL, which should resemble `https://rag-showcase-api.onrender.com`.
14. Test these URLs in order:

    ```bash
    curl --fail https://YOUR-SERVICE.onrender.com/api/health
    curl --fail https://YOUR-SERVICE.onrender.com/api/demo/config
    curl --fail https://YOUR-SERVICE.onrender.com/api/documents
    ```

    The config response should contain `"enabled":true`. The documents response may initially be `[]` while background seeding runs.

The demo Docker image intentionally excludes PyTorch and sentence-transformers. Qdrant Cloud performs the same MiniLM embedding operation, allowing FastAPI to fit on Render's small free instance.

Render sleeps a free service after inactivity. The first interview request can take roughly a minute. Open the health URL a few minutes before a live demonstration; do not use an automated keep-alive service to evade free-plan policies.

### 3.3 Common first-deploy failures

- **Settings validation mentions `QDRANT_URL` or `QDRANT_API_KEY`:** one of the Render values is missing or was pasted into the wrong field.
- **Qdrant returns 401/403:** replace `QDRANT_API_KEY` with a valid Database API key that has manage/write permission.
- **Cloud inference disabled/model unavailable:** revisit the Qdrant cluster's Inference tab and confirm the exact free MiniLM model.
- **Health check remains 503:** Qdrant is unavailable, suspended, or the endpoint/key is incorrect. Check the Render log immediately before the health request.
- **Health works but documents stay empty:** inspect the auto-seed log, then call the manual seed endpoint in step 5.

## 4. Deploy the Vercel frontend

### 4.1 Create the frontend project

1. Sign in to [Vercel](https://vercel.com/) with GitHub and remain on the Hobby plan.
2. Choose **Add New → Project**, find the same `rag-knowledge-assistant` repository, and click **Import**.
3. Use a project name such as `rag-knowledge-assistant` or `rag-showcase`. The available name determines the generated `.vercel.app` hostname.
4. Set **Root Directory** to:

   ```text
   frontend
   ```

5. Confirm the framework preset is **Vite**. `frontend/vercel.json` supplies the expected build command (`npm run build`), output directory (`dist`), SPA rewrite, and security headers.
6. Add one environment variable for **Production**:

   ```text
   VITE_API_BASE_URL=https://YOUR-SERVICE.onrender.com/api
   ```

   Include `/api`, but do not include a trailing slash. This value is expected to be public because Vite embeds it into the browser bundle.
7. Do not add `DEMO_MODE`, `VITE_API_KEY`, the LLM key, the Qdrant key, the hCaptcha secret, or `ADMIN_API_KEY` to Vercel.
8. Click **Deploy** and wait for the production build to finish.
9. Copy the final production origin, for example `https://rag-knowledge-assistant.vercel.app`.

### 4.2 Join the frontend and backend

1. In Render, open **rag-showcase-api → Environment**.
2. Replace `CORS_ORIGINS=https://placeholder.invalid` with the exact Vercel origin. Include `https://`, but no path or trailing slash.
3. Choose **Save and deploy**.
4. In hCaptcha, open the `rag-showcase` sitekey. If domain allowlisting is available, enable it and add the Vercel hostname without `https://` or a path.
5. Reload the Vercel site after the Render deploy finishes.

Preview deployment hostnames change for each branch. This guide intentionally permits only the stable production Vercel origin in CORS. Use the production deployment for interviews.

If the page loads but says the API is unavailable, inspect the browser Network panel. A CORS error usually means `CORS_ORIGINS` does not exactly match the Vercel origin; a timeout often means the Render Free service is waking up.

Vercel Hobby permits personal, non-commercial projects. Recheck its terms if the site becomes a business or paid service.

## 5. Seed or refresh the corpus

`DEMO_AUTO_SEED=true` starts an idempotent background seed after the backend launches. It ingests any missing entries from `backend/demo_documents.json`.

To manually retry seeding:

```bash
curl --fail --request POST \
  --header "X-Admin-Key: YOUR_RENDER_ADMIN_KEY" \
  https://YOUR-SERVICE.onrender.com/api/admin/seed
```

The initial seed downloads three public ArXiv papers, extracts and chunks them, and sends the text to free Qdrant Cloud inference. It can take several minutes. Repeating the operation skips documents already identified by their source URL.

Edit `backend/demo_documents.json` to change the curated corpus, descriptions, or example questions. Prefer public-domain, Creative Commons, or clearly redistributable material. The UI links to original sources instead of hosting the PDFs itself.

## 6. Validate the live deployment

```bash
curl --fail https://YOUR-SERVICE.onrender.com/api/health
curl --fail https://YOUR-SERVICE.onrender.com/api/demo/config
curl --fail https://YOUR-SERVICE.onrender.com/api/documents
```

Then verify in the browser:

1. The document library lists the three curated papers.
2. Chunk inspection opens and source links point to ArXiv.
3. A query cannot be submitted before hCaptcha succeeds.
4. Selecting one paper scopes returned citations to that document.
5. Expanding **Retrieval trace** shows chunk text, score, page, and section.
6. Repeating the same question reports a cached response.
7. `/api/ingest` returns `401` without the admin key.
8. The Qdrant dashboard and MCP endpoint are not linked or deployed publicly.

## Protections and limits

- Per-client hourly limit: 10 requests by default.
- Global daily uncached-generation limit: 50 by default, persisted in Qdrant across Render restarts.
- Repeated normalized questions are cached in the API process.
- Question length: 500 characters in showcase mode.
- Retrieval scope: at most five selected documents.
- hCaptcha is verified server-side and its tokens are single-use.
- Ingestion and re-seeding require `X-Admin-Key`.
- URL, redirect, content-type, upload-size, PDF-signature, context-size, and retrieval-count validation remain active.
- Only the FastAPI service receives provider secrets.

The hourly in-memory limit resets on a Render cold start, which is why hCaptcha and the persistent global cap are both enabled. Also monitor the dedicated OpenAI/Anthropic project and configure the smallest provider-side usage controls available; do not assume a budget alert automatically blocks requests.

## Interview-day checklist

- Open the Render health URL and wait for a healthy response.
- Open Qdrant Cloud and reactivate the cluster if it was suspended.
- Confirm `/api/documents` lists the corpus.
- Run one sample question and expand its retrieval trace.
- Check the LLM provider's current usage and budget.
- Keep screenshots or the README examples available as a fallback if a free service cold-starts or a provider is unavailable.

## Local showcase mode

Local Docker can exercise the same UI while keeping local sentence-transformers and Qdrant:

```env
DEMO_MODE=true
DEMO_AUTO_SEED=true
ADMIN_API_KEY=choose-a-long-random-local-value
EMBEDDING_PROVIDER=local
HCAPTCHA_SITE_KEY=
HCAPTCHA_SECRET=
```

Then run:

```bash
docker compose up --build -d
docker compose logs -f backend
```

Open `http://localhost:5173`. Local CAPTCHA is disabled when both hCaptcha variables are empty; rate limits, document selection, admin-only ingestion, caching, and the global daily cap remain enabled.
