# Publishing this (2 minutes)

You said you'd rather push this yourself than hand me a token, so here's the
exact copy-paste path: create the GitHub repo, push, and turn on Pages.

## 1. Create the repo and push

```bash
cd composio-app-research   # this folder

# if you haven't already:
git add -A
git commit -m "AI Product Ops take-home: 100-app buildability study"

# create a new repo on GitHub (pick one):
gh repo create composio-app-research --public --source=. --remote=origin --push
# --- or, without the gh CLI ---
# 1. create an empty repo at https://github.com/new (name: composio-app-research, no README/gitignore)
# 2. then:
git remote add origin https://github.com/<your-username>/composio-app-research.git
git branch -M main
git push -u origin main
```

## 2. Turn on GitHub Pages

1. On GitHub, go to your new repo → **Settings → Pages**.
2. Under "Build and deployment" → Source: **Deploy from a branch**.
3. Branch: **main**, folder: **/ (root)**. Save.
4. Wait ~30–60 seconds, then your live page is at:
   `https://<your-username>.github.io/composio-app-research/`

(There's a root-level `index.html` already in this repo — a copy of
`site/index.html` — specifically so GitHub Pages works with zero extra
config. `site/index.html` stays the canonical source location referenced in
the README.)

## 3. Fill in the two links

Once both are live, open `README.md` at the repo root and replace the two
placeholder lines near the top with your actual URLs, then:

```bash
git add README.md
git commit -m "Add live links"
git push
```

That's it — those are the two links to submit: the live page
(`https://<your-username>.github.io/composio-app-research/`) and the repo
itself (`https://github.com/<your-username>/composio-app-research`).
