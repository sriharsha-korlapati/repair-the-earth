# Hosting Carbon Intelligence v2

The app is a standard Streamlit application with no database, no build step and no
server-side state, so hosting is genuinely a five-minute job once the code is on
GitHub.

## Streamlit Community Cloud (what `rte-carbon.streamlit.app` already uses)

Free, and it redeploys automatically on every push.

1. Go to <https://share.streamlit.io> and sign in with the GitHub account that
   owns `sriharsha-korlapati/repair-the-earth`.
2. **New app → Deploy a public app from GitHub**, then set:

   | Field | Value |
   | --- | --- |
   | Repository | `sriharsha-korlapati/repair-the-earth` |
   | Branch | `claude/carbon-emissions-dashboard-v2-jl7g2c` (or `main` once merged) |
   | Main file path | `app.py` |
   | Python version | 3.11 or newer |

3. **Deploy.** The first build installs `requirements.txt` (Streamlit, Plotly,
   pandas, anthropic) and takes two or three minutes. Later pushes to the same
   branch redeploy in seconds.

To update the existing `rte-carbon` app in place instead of creating a second
one, open it from your Streamlit Cloud dashboard, choose **Settings → General**,
and switch its branch to this one. That keeps the URL your team already has.

### Optional: switch on the AI coach

The dashboard is fully functional without this — every number, recommendation and
insight is computed locally. The key only enables the conversational coach.

In the app's **Settings → Secrets**, paste:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

Streamlit restarts the app and `core/ai.py` picks the key up automatically. The
key lives in Streamlit's secret store, never in the repository — `.gitignore`
already excludes `.streamlit/secrets.toml` so a local key cannot be committed by
accident.

**Cost note:** every question on the coach page is an API call billed to that key.
If you are demoing on a shared screen at TerraThon, either leave the key out (the
page falls back to the offline engine and says so) or expect a few rupees of usage.

## Running it locally

```bash
git clone https://github.com/sriharsha-korlapati/repair-the-earth
cd repair-the-earth
git checkout claude/carbon-emissions-dashboard-v2-jl7g2c
pip install -r requirements.txt
streamlit run app.py
```

Optional, for the coach:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Before you demo on someone else's Wi-Fi

- **Run it locally as a fallback.** A hosted app is one bad venue connection away
  from being a black screen. Have `streamlit run app.py` working on the laptop you
  present from.
- **Load the page once beforehand.** Community Cloud puts free apps to sleep after
  inactivity, and the first visitor waits through a cold start.
- **Check the fonts and charts render** on the projector resolution you will
  actually use.

## Other hosts

Nothing in the app is Streamlit-Cloud-specific. It is a single process that
listens on one port:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

That line is all Railway, Render, Fly.io or a plain VM needs, with
`requirements.txt` as the install step. There is no database to provision and no
state to persist — every session is self-contained in the browser tab.
