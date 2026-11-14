# Online Catalog Studio — one-time setup

After setup, you and your staff use an online link. No one needs to start a local server, run a build, or push products manually.

## What is included

- A private sign-in page and mobile-friendly product editor.
- Add, edit and remove products; upload pictures; change best-seller and stock flags.
- Saving sends the product and its image to your GitHub repository together.
- Your existing GitHub Actions workflow builds and deploys the public catalog.
- The panel shows when an update is saved, publishing, live, or failed.
- Conflicting edits are rejected so one staff member cannot silently overwrite another.
- Repeat submissions of the same new product do not add it twice.
- Your existing local catalogger and public catalog design are unchanged.

This version gives every configured account permission to add, edit, remove and publish products. Owner approvals and self-service staff invitations are not included. Removing a product preserves its original image and Git history for recovery.

## Current handoff status

The hosted application has been implemented and tested locally. It has NOT been deployed to Render or tested against a live GitHub token. The local session could not resolve github.com. Do not treat these files as a live admin service until the setup and deployment verification below are complete.

## 1. Put the hosted files on GitHub once

The following new files belong at the root of your existing `SyedAbdullahHashmi/rya-catalog` repository:

- `render.yaml`
- the full `hosted/` folder

Keep your current `catalogs/`, `images/`, `build_catalogs.py`, and `.github/workflows/pages.yml` in the repository. They are used as they are. The public builder currently publishes three collections: men’s jewellery/accessories, women’s jewellery/accessories and women’s clutches. The separate legacy `mens_accessories.json` is intentionally not offered by this panel because the current builder does not publish it.

If these changes are already committed in the working repository, push that commit with GitHub Desktop or Terminal. Review outgoing changes and fetch/pull before pushing if the online repository has changed. Never force-push over an update from someone else.

Do not use the old ZIP from before this hosted version was created; it does not contain this online admin panel.

## 2. Give the server permission to update the catalog

Only you do this once. Staff will not need GitHub accounts.

1. Sign in to the GitHub account that owns the repository.
2. Open https://github.com/settings/personal-access-tokens and choose **Generate new token**.
3. Give it a clear name, such as `RYRA catalog admin`, and choose an expiry date you can maintain.
4. Select **Only select repositories**, then select **rya-catalog**.
5. Set repository permissions: **Contents → Read and write** and **Actions → Read-only**. Leave other permissions at their defaults.
6. Generate the token and copy it directly into Render’s `GITHUB_TOKEN` field in the next step. Do not send it in chat, paste it in code, or store it in your repository.

This token lets the hosted application publish changes to the selected repository. A GitHub App can replace it later for automatically renewable credentials. If branch protections require pull requests, direct publishing will be blocked; use a publishing flow compatible with those rules rather than disabling protections.

## 3. Deploy the private panel on Render

1. Sign in at https://dashboard.render.com using your own account.
2. Choose **New → Blueprint** and connect the `rya-catalog` repository. If connecting GitHub asks for repository access, select only this repository.
3. Render reads the included `render.yaml` and offers a web service called `ryra-catalog-admin`.
4. Review the plan. The supplied configuration requests the **Free** plan. If Render requires payment details or offers a paid plan, review that choice yourself before proceeding. Free services can sleep after inactivity, so the first visit may take longer; this does not stop the public GitHub Pages catalog.
5. Fill in these fields when prompted:

| Setting | What to enter |
| --- | --- |
| `GITHUB_TOKEN` | The token from step 2, entered directly in Render |
| `ADMIN_EMAIL` | The email you want to use to sign in to Catalog Studio |
| `ADMIN_PASSWORD` | A unique password of at least 14 characters, entered directly in Render |

`SESSION_SECRET` is generated automatically. `GITHUB_REPOSITORY` and `GITHUB_BRANCH` already point to your catalog’s `main` branch. Do not enable `ALLOW_LOCAL_HTTP` in Render.

6. Deploy and wait for the service to report **Live**.
7. Open the actual `onrender.com` URL shown by Render. Sign in with the admin email/password you just set. This is the link to bookmark and share with staff after adding their accounts.

If deploying a Blueprint is unavailable, create a **Web Service** from the same repository with these settings:

| Setting | Value |
| --- | --- |
| Runtime | Python 3 |
| Root directory | Leave blank |
| Build command | `pip install -r hosted/requirements.txt` |
| Start command | `gunicorn 'hosted.app:create_app()' --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180 --access-logfile -` |
| Health check | `/healthz` |
| Auto deploy | Off |

Also add all environment variables declared in `render.yaml`. For a manual service, use Render’s secret generator for `SESSION_SECRET` (at least 32 random characters).

Auto deploy is off intentionally: adding a product does not need to restart the admin panel. When application CODE changes, manually deploy the new commit in Render once. Product DATA changes continue to publish through GitHub Actions automatically.

## 4. Check publishing once

1. Confirm the real products load in the panel. If they do not, check the token, repository, branch and Render logs.
2. Sign out and confirm that visiting the panel requires signing in again.
3. Sign back in and make an intentional, reversible update to one real product, such as its best-seller flag.
4. Click **Save & publish**. First you should see **Update saved**, then **Publishing**, then **Catalog published**.
5. Open the public catalog and confirm the intended change. Restore the flag if it was only a test.
6. Confirm the GitHub repository has a new commit and its **Build & Deploy Catalogs** workflow completed successfully.

Product information is stored in GitHub, not on Render’s temporary disk. Restarting or redeploying the panel does not erase products. Password changes or restarts can require staff to sign in again.

## Add or remove staff

Staff use their own email/password for THIS panel. They do not need GitHub or Render accounts.

1. From a copy of the repository, run this one-time owner setup command:

   ```sh
   python3 -m hosted.accounts
   ```

2. Enter the staff member’s email and a unique password. The password is hidden while typing. The tool prints a JSON entry containing a password hash, not the password itself.
3. In Render → your service → **Environment**, edit `STAFF_ACCOUNTS_JSON`. Add that entry to the existing JSON object. For multiple users, keep all entries inside one pair of braces, separated by commas. Do not replace everyone’s existing entries when adding one person.
4. Save and redeploy. Give the staff member the panel link and their credentials through your usual private channel.
5. To remove access, delete their email entry from `STAFF_ACCOUNTS_JSON`, save and redeploy. Their old session will stop working. To reset their password, generate a new hash for that account and replace its entry.

This owner setup is only for account changes. Product uploads never need your local computer.

## Daily use

1. Open the admin link and sign in.
2. Choose the collection and enter the product details. Prices must be numbers in rupees, such as `1999`.
3. Choose a photo up to 8 MB, or use a public HTTPS image link.
4. Click **Save & publish** once and wait for confirmation. Do not close the page while saving.
5. Wait for **Catalog published** before expecting the public site to show the update.

If someone else changed the same collection, your save will stop instead of overwriting their work. Use Reload and review the current products. Reload clears an existing edit form so product indices cannot shift underneath an edit; for a new product, the entered fields are retained.

If a request times out, the result is unconfirmed. Check publishing and reload the collection before retrying. Repeating the same add submission is protected against duplicate creation. A failed deployment does not delete the saved product; the owner can rerun the existing workflow from GitHub Actions.

## Maintenance

- Renew the GitHub token before expiry by replacing `GITHUB_TOKEN` in Render.
- Retain the same `SESSION_SECRET` across routine redeploys; changing it signs everyone out.
- Keep one Gunicorn worker as configured; login throttling is held in memory and resets on restart. For a larger deployment, add a shared rate limiter before scaling workers/instances.
- GitHub commit history records each change with a pseudonymous staff identifier and operation identifier. Staff login email addresses are not published in commit messages.
- Keep all tokens, account configuration and passwords in Render’s environment settings, never in the public GitHub repository.
- The free hosting plan’s current limitations are documented at https://render.com/docs/free.

## Technical checks

Run from the repository root:

```sh
python3 -m unittest discover -s hosted/tests -v
node --check hosted/static/app.js
```

Tests use a fake GitHub service. They cover login/session protection, CSRF, failed saves, image and price validation, stale edits, duplicate submissions, preservation of existing products and atomic Git writes. They do not establish a real Render deployment or a successful live GitHub publish.

Reference documentation: https://render.com/docs/blueprint-spec and https://docs.github.com/en/rest/git/refs.
