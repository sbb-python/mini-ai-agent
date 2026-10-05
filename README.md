# RepoGuide

RepoGuide is a small AI assistant for exploring **any public GitHub repository**. The website is static and deploys to GitHub Pages; its Python API runs separately on Render and uses OpenRouter's free-model router to answer questions using repository files.

## Run locally

1. Install Python 3.10 or newer.
2. Create and activate a virtual environment, then install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Copy the example environment file and open `.env`:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   Replace the example value with your **new** OpenRouter API key. `.env` is ignored by Git; never commit or share it.

4. Start the backend from the project root, loading `.env`:

   ```powershell
   uvicorn backend.main:app --reload --env-file .env
   ```

5. Open `frontend/index.html` in a local web server (for example, with VS Code Live Server). The default API URL in `frontend/config.js` is `http://localhost:8000`.

## Deploy the backend to Render

1. Push this repository to GitHub.
2. In Render, create a new **Blueprint** from the repository and use `render.yaml`.
3. Create an OpenRouter API key in [OpenRouter](https://openrouter.ai/settings/keys) and set `OPENROUTER_API_KEY` in the Render service environment. Free models have limited availability and rate limits. The service URL will look like `https://repoguide-api.onrender.com`.
4. Replace the `apiBaseUrl` value in `frontend/config.js` with that service URL.
5. In Render, set `FRONTEND_ORIGINS` to your Pages origin, such as `https://yourname.github.io`. Do not include the project path; browser origins contain only the scheme and host. Separate multiple origins with commas.
6. Commit and push the `config.js` update.

Never put the OpenRouter API key in frontend files or commit it to GitHub.

## Deploy the website to GitHub Pages

1. In the GitHub repository, open **Settings → Pages** and set the build and deployment source to **GitHub Actions**.
2. Push to the `main` branch (or run the **Deploy GitHub Pages** workflow manually from the Actions tab).
3. Open the Pages URL shown in the workflow deployment.

The Pages workflow publishes only the `frontend` directory. Configure the Render backend first and update `frontend/config.js` before relying on the published site.

## How it works

- The browser sends a repository URL and question to the Python API; the OpenRouter key stays on Render.
- The API accepts `github.com/owner/repository` public URLs, reads the default branch, and fetches a small set of relevant text files through GitHub's public API.
- Repository files are treated as untrusted data. The assistant is instructed to cite file paths and say when the available source excerpts are insufficient.
- The unauthenticated GitHub API has rate limits. GitHub may ask the service to wait before it can inspect more repositories.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | OpenRouter API key (backend only) | Required |
| `OPENROUTER_MODEL` | OpenRouter model or router ID | `openrouter/free` |
| `FRONTEND_ORIGINS` | Comma-separated browser origins allowed by the API | `*` |

Set `FRONTEND_ORIGINS` to the exact website origin for deployment rather than `*`.

OpenRouter's free model availability, rate limits, and provider data policies can vary. Review the [free models documentation](https://openrouter.ai/docs/guides/routing/model-variants/free) and the terms for the selected model provider before using the app.
