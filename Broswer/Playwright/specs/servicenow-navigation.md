# ServiceNow Developer Portal — Sign In and Navigate

> Plan produced by the 🎭 planner agent after exploring the live site
> (`https://developer.servicenow.com/dev.do`). Selectors below were verified
> against the real DOM.

## Seed
- `seed.spec.ts` — navigates to `https://developer.servicenow.com/dev.do`

## Environment / Data
- Username: `SERVICENOW_USERNAME` env var (loaded from `.env`)
- Password: `SERVICENOW_PASSWORD` env var (loaded from `.env`)

## Verified facts about the app
1. The homepage shows a cookie banner with an **"Accept and Proceed"** button that
   overlays the page and intercepts clicks. Dismiss it first.
2. **Sign In** is a `button` named `"Sign In"` (role=button), located in the
   utility menu. Clicking it redirects to `https://signon.servicenow.com/...`.
3. The login form is a **single page, two-step** flow:
   - `Email` textbox (role=textbox, name "Email")
   - `Next` button — disabled until a valid email is entered. Clicking it reveals
     the password field **on the same page** (URL stays `pageId=login`).
   - `Password` textbox (role=textbox, name "Password")
   - `Sign in` button (note: lowercase "in") — disabled until password entered.
4. On success the browser redirects back to `https://developer.servicenow.com/dev.do`
   and the **"Sign In"** button is replaced by a **"User Profile"** `menuitem`.
   That swap is the reliable signal that authentication succeeded.
5. The primary nav exposes mega-menu **buttons**: `MyNow`, `Products`,
   `Industries`, `Learning`, `Support`, `Partners`, `Company`. These are rendered
   inside web components and open on hover. On the authenticated home page a
   `dps-home-auth-quebec` element overlaps the header and intercepts pointer
   events, so the menu buttons may require a forced/dispatched interaction.

## Scenarios

### Scenario 1: Sign in succeeds
**Steps**
1. Navigate to the Developer Portal homepage.
2. Dismiss the cookie banner ("Accept and Proceed") if present.
3. Click the **Sign In** button — expect redirect to `signon.servicenow.com`.
4. Fill the **Email** textbox with `SERVICENOW_USERNAME`.
5. Click **Next** — the **Password** textbox appears on the same page.
6. Fill the **Password** textbox with `SERVICENOW_PASSWORD`.
7. Click **Sign in**.

**Expected outcomes**
- Browser redirects back to `developer.servicenow.com/dev.do`.
- No "Invalid username or password" error is shown.
- A **"User Profile"** menuitem is visible (Sign In button is gone).

### Scenario 2: Invalid credentials show an error
**Steps**
1. Navigate to homepage, dismiss cookie banner, click **Sign In**.
2. Fill **Email** with an address, click **Next**.
3. Fill **Password** with a wrong value, click **Sign in**.

**Expected outcomes**
- An error message (e.g. "Invalid username or password" / "incorrect") is shown.
- The user stays on `signon.servicenow.com` (not authenticated).

### Scenario 3: Open the Industries mega-menu (authenticated)
**Steps**
1. Complete Scenario 1 (signed in).
2. Open the **Industries** mega-menu from the primary navigation.

**Expected outcomes**
- The Industries menu expands and shows its industry links (e.g. Automotive).

> Note: the mega-menu lives in a web component and the home content overlaps the
> header, so the generated test forces the interaction. Run the 🎭 healer if the
> menu structure changes.
