# Deploying the KisaanRaksha dashboard (Streamlit Community Cloud)

The dashboard is a Streamlit app, so it needs a **persistent server** — it cannot
run on Vercel/Netlify (serverless). Streamlit Community Cloud is free and
deploys straight from this GitHub repo.

## Steps (~3 minutes)

1. Go to **https://share.streamlit.io** and sign in with the GitHub account
   that owns the repo (`sahilkarande0918-cmd`).
2. Click **Create app → Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `sahilkarande0918-cmd/Kisan-Raksha-project`
   - **Branch:** `main`
   - **Main file path:** `dashboard/app.py`
4. Open **Advanced settings**:
   - **Python version:** 3.12 (or 3.13)
   - **Secrets:** paste the single line below (real key from your `.env`):
     ```
     DATA_GOV_IN_API_KEY = "paste-your-key-from-.env-here"
     ```
     (Weather and NDVI need no key; the mandi tool also has an offline fallback,
     so the app still runs even without this — but add it for live prices.)
5. Click **Deploy**. First build takes a few minutes (installing lightgbm etc.);
   the first page load then pulls live signals for 16 districts (~30–60 s),
   after which it is cached for 10 minutes.

You get a public URL like `https://kisan-raksha-project.streamlit.app` to share
with judges.

## Notes
- `.streamlit/config.toml` (light green theme) is already in the repo and applies
  automatically.
- Do **not** commit a filled-in `.streamlit/secrets.toml` — it is gitignored.
  Secrets live only in the Streamlit Cloud UI.
- The WhatsApp webhook (`api/webhook.py`) is a **separate** service and is not
  part of this deployment — it needs a persistent host too (Render/Railway) or
  the local `uvicorn + ngrok` setup used for the demo.
