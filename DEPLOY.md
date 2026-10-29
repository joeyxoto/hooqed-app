# Deploying Hooqed v0 to Render

You need: your GitHub account (the empty private repo **hooqed-app**), your Render account (already linked to GitHub), an xAI account, and a Resend account. Keys are pasted **only** into Render's Environment page. Never into chat, email, or a file in the repo.

---

## 1. Get the code into `hooqed-app`

### Route A (preferred): Goji pushes it
1. In the Grok Bot app, when Goji asks to connect GitHub, click the one-click sign-in.
2. On GitHub's permission screen choose **Only select repositories**, pick **hooqed-app**, and approve. Goji gets no access to your other repos.
3. Goji pushes the `main` branch to `hooqed-app` and tells you when it's done. Nothing else in your account changes.

### Route B (fallback): upload a zip in the browser
1. Goji sends you `hooqed-app.zip` (about 0.3 MB, 61 files, no file over 1 MB, so it fits GitHub's limits of 100 files per upload and 25 MiB per file in one go).
2. Unzip it on your computer. You get a folder with `app`, `engine`, `hooq_templates`, `Dockerfile`, `render.yaml` and so on.
3. Open `https://github.com/<your-username>/hooqed-app`. On the empty repo page click the link **uploading an existing file**.
4. Open the unzipped folder, select **everything inside it** (not the folder itself) and drag it onto the page. Folders keep their structure.
   - Hidden files: `.gitignore`, `.dockerignore` and `.env.example` start with a dot. On a Mac press **Cmd+Shift+.** in Finder to show them first, then select all. (If they are missed, the app still deploys; they just keep the repo tidy.)
5. Commit message: `Hooqed v0`. Leave **Commit directly to the main branch** selected. Click **Commit changes**.
6. Check the repo now shows `render.yaml` and `Dockerfile` at the top level (not inside a sub-folder).

---

## 2. Render

### 2a. Limit Render to this one repo
1. On GitHub, click your profile picture (top right) > **Settings**.
2. Left menu > **Integrations** section > **Applications** > tab **Installed GitHub Apps** (direct link: `https://github.com/settings/installations`).
3. Next to **Render** click **Configure**.
4. Under **Repository access** choose **Only select repositories** > **Select repositories** > pick **hooqed-app**. Remove any others you don't want Render to see.
5. Click **Save**.

### 2b. Create the service from the Blueprint
1. Go to `https://dashboard.render.com`. Top right: **+ New** > **Blueprint**.
2. Pick **hooqed-app** from the repository list (click **Connect**).
3. Blueprint name: `hooqed`. Branch: `main`. Render reads `render.yaml` and shows one web service **hooqed** (Docker, Standard plan, 1 GB disk at `/data`, Frankfurt).
4. Render asks for the values marked "sync: false": `XAI_API_KEY`, `RESEND_API_KEY`, `MAIL_FROM`, `BASE_URL`. Paste them here (see section 3). For `BASE_URL`, put `https://hooqed.onrender.com` for now; fix it in step 7 if Render picks a different address.
5. Click **Deploy Blueprint** (some screens say **Apply**). Render needs a card on file for the Standard plan and the disk.
6. The first build takes about 5–10 minutes (it installs Chrome). Wait for **Live**.
7. Open the service: the URL is under its name, e.g. `https://hooqed-ab12.onrender.com`. If it differs from what you typed, go to **Environment** > edit `BASE_URL` to that exact URL > **Save, rebuild, and deploy**.
8. Open the URL. You should get the Hooqed sign-up page. `<url>/healthz` should say `{"ok":true}`.

Cost on Render: Hobby workspace $0 + Standard web service $25/month + 1 GB disk $0.25/month = **$25.25/month** (about £19). Billed per second.

Note: because the service has a disk, each deploy restarts it, so it is unavailable for a short moment during deploys. A build that is running at that moment restarts automatically.

---

## 3. The values (paste each one only into Render > hooqed > Environment)

| Variable | Where you get it |
|---|---|
| `XAI_API_KEY` | `https://console.x.ai` > sign in > **API Keys** > **Create API key** (name it `hooqed`). Copy it once and paste into Render. Add prepaid credit under **Billing** (about 18p of AI per new hooq; re-saving the owner check costs nothing). |
| `RESEND_API_KEY` | `https://resend.com` > sign up (Free plan) > **API Keys** > **Create API Key**, permission **Sending access**. Copy into Render. |
| `MAIL_FROM` | First add your domain in Resend: **Domains** > **Add Domain** (use a sub-domain such as `mail.hooqed.ai`, so the Replit site on hooqed.ai is untouched), then add the DNS records Resend shows at your domain registrar and wait for **Verified**. Then set `MAIL_FROM` to e.g. `Hooqed <leads@mail.hooqed.ai>`. |
| `BASE_URL` | Your Render service URL from step 2b.7, e.g. `https://hooqed-ab12.onrender.com` (no trailing slash). Later, your own domain. |
| `SECRET_KEY` | Nothing to do. Render generates it from `render.yaml`. |

Until Resend is set up you can leave `RESEND_API_KEY` empty: the app runs, leads still appear in the dashboard, and the log says "email skipped".

Changing any value: Environment > edit > **Save, rebuild, and deploy**.
