# RepoGuide

Ask questions about any public GitHub repository. The app uses Python and Streamlit; GitHub is used to read public repository files and OpenRouter provides AI answers, so an internet connection is required.

## Run locally on Windows

1. Install Python 3.10 or newer.
2. From this folder, create and activate a virtual environment, then install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. If you do not already have a local `.env` file, copy the example:

   ```powershell
   Copy-Item .env.example .env
   ```

   Open `.env` and replace the example value with a **new OpenRouter API key**. The key previously shared in chat should be revoked and must not be reused. Keep `.env` private; it is excluded from Git.
4. Start the app from the project folder:

   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
   ```

5. Open <http://localhost:8501/> in your browser. Stop the app with `Ctrl+C`.

When run locally, the service binds to `127.0.0.1` and is available only on your computer. Questions and selected public-repository excerpts are sent over the internet to OpenRouter for answers. OpenRouter's free model availability and request limits may vary.

## Deploy online with Streamlit Community Cloud

1. Push this project to a GitHub repository. The repository must include `app.py`, `backend/`, and `requirements.txt`.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app from that repository, select the `main` branch, and set the main file path to `app.py`.
3. In **Advanced settings → Secrets**, add:

   ```toml
   OPENROUTER_API_KEY = "your-new-openrouter-key"
   ```

4. Deploy the app. Do not put the API key in GitHub, `app.py`, or any committed file. The public GitHub repository makes the source code visible to everyone.

Free Community Cloud apps may sleep when unused and take a short time to wake up. Questions and selected excerpts from public repositories are sent to OpenRouter.

## Troubleshooting

- If the key is rejected, confirm that `OPENROUTER_API_KEY` in `.env` contains a valid replacement key.
- If GitHub or OpenRouter reports a rate limit, wait and try again later.
- Empty public repositories cannot be analyzed until they contain at least one pushed file.
