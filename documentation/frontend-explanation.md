# GramSathi AI Frontend: What, How, and Why

This guide explains the current frontend: what it contains, how a user moves through it, how the code is organized, why the implementation uses its current techniques, and when alternatives would make sense.

It describes the implementation in `frontend/` as it exists today. It is not a promise that every visible dashboard shortcut is connected to a production service.

## 1. What the frontend does

The frontend is a browser-based React single-page application for GramSathi AI. It provides:

- A public landing page introducing farming and citizen/legal-information assistants.
- Login and account-registration screens.
- A dashboard after sign-in.
- Separate FarmSathi and NyayaSathi question-and-answer experiences.
- A conversation-history screen.
- Hindi and English interface text.
- An API layer that talks to the backend and can provide demo responses during development.

The frontend is the presentation and interaction layer. It collects input, calls the backend, and displays results. It does not itself establish a user's identity, decide legal eligibility, or produce authoritative agricultural/legal advice. Those responsibilities belong to backend services and trusted sources.

## 2. Source files and responsibilities

| File | Responsibility |
| --- | --- |
| `frontend/index.html` | Browser document, viewport metadata, page title, and root element. |
| `frontend/src/main.jsx` | Creates the React root, renders `App`, and imports the stylesheet. |
| `frontend/src/App.jsx` | Application state, language text, page selection, forms, dashboard, chat, and history UI. |
| `frontend/src/api.js` | HTTP requests, auth/chat/history functions, and development demo behavior. |
| `frontend/src/styles.css` | Visual design, responsive layout, focus styles, and reduced-motion behavior. |
| `frontend/vite.config.js` | Vite/React setup and the development `/api` proxy to the backend. |
| `frontend/package.json` | Frontend commands and runtime/build dependencies. |
| `frontend/.env.example` | Example API URL and demo-mode configuration. |

### Rendering path

1. The browser loads `index.html`.
2. Its module script loads `src/main.jsx`.
3. `main.jsx` calls React's `createRoot` for `#root`.
4. React renders `App`, which selects the current screen.
5. `App.jsx` imports `api.js` for backend operations and `styles.css` for presentation.

This is a client-rendered single-page application: changing screens updates React state instead of asking the server for a separate HTML page.

## 3. Technologies used

### React and JSX

**What:** React components describe pieces of the interface. JSX lets the JavaScript file express the HTML-like structure of those pieces.

**Why it fits this frontend:**

- The interface is made from reusable screens and controls: `Landing`, `Auth`, `Home`, `Chat`, and `History`.
- Forms, language changes, loading indicators, errors, and messages all change over time. React state makes those changes explicit and re-renders affected UI.
- Components keep related behavior and markup close together without introducing another rendering system.

**Why not plain DOM manipulation?** Directly creating, replacing, and updating DOM nodes would require manually keeping the UI synchronized with auth state, chat state, language, and history. That becomes fragile as the number of interactive states grows.

**Why not another framework?** Vue, Svelte, and Angular can all build this kind of app. React is the choice already used by this project and is sufficient for its current scope. Replacing it would add migration work without a concrete feature benefit.

### Vite

**What:** Vite runs the local development server and bundles the frontend for production.

**Why it fits:**

- The app is a client-rendered React application and does not currently need server-side rendering.
- The project has a small build configuration and a quick feedback loop.
- Vite already provides the React plugin, development server, environment-variable handling, and production build used here.

**Why not Next.js or another server-rendering framework?** Server rendering can improve first-page HTML delivery, indexing, and server-side routing. Those are not current requirements for the authenticated chat application. If public pages later need search-engine rendering, server routes, or richer deep-link behavior, a framework with SSR could be evaluated then.

### JavaScript

**What:** The React components and API layer are JavaScript files (`.jsx`/`.js`).

**Why it fits now:** The frontend is a relatively small application, and JavaScript avoids introducing a type-checking and build configuration migration for this UI change.

**Trade-off:** JavaScript does not catch all wrong property names, response-shape mismatches, or invalid state values before runtime. TypeScript would be a sensible next step as the API contracts and component count grow. It is not necessary to adopt it just to render these screens.

### Native CSS

**What:** `styles.css` uses regular CSS, CSS custom properties, layout primitives such as Grid and Flexbox, and media queries.

**Why it fits:**

- The reference design needs custom colors, shapes, cards, and illustration-like artwork.
- CSS custom properties keep recurring colors, radii, and surfaces in one place.
- Grid and Flexbox support the desktop layouts and their mobile rearrangements without adding a styling runtime or package.
- The CSS illustration avoids requiring external image files or an additional illustration library.

**Why not Bootstrap or a component library?** A component library can speed up standard administrative interfaces, but this design needs a more distinctive visual system. Adding a library would increase dependencies and could require substantial overrides to achieve the reference's look.

**Why not Tailwind?** Utility classes are a valid choice, particularly in teams that standardize on them. This project currently has one shared stylesheet and custom visual components, so plain CSS is direct and avoids adding a build dependency or changing the project's styling convention.

**Trade-off:** A shared stylesheet can accumulate global selectors and become harder to maintain as the app grows. CSS Modules or a component-scoped styling system would be worth considering if unrelated pages begin conflicting over class names.

## 4. Application state and screen selection

`App` owns state that is shared across screens:

- `lang`: selected interface language (`hi` or `en`).
- `user`: the signed-in user object, if one is stored.
- `view`: which screen to show (`landing`, `auth`, `home`, `chat`, or `history`).
- `authMode`: whether the auth form is in login or registration mode.
- `asst`: selected assistant (`farm` or `nyaya`).
- `msgs`: messages passed into the current conversation.

The app uses React's `useState` because these values are small and have a clear owner. `App` passes the actions a child needs as props, for example `onPick`, `onHistory`, or `onDone`.

### Why not a router?

The current screens are a small set of application states and are not represented by separate URLs. Switching `view` is simple and keeps the dependencies small.

This means the browser URL does not currently provide deep links to a particular assistant, conversation, or auth mode, and browser Back/Forward does not necessarily mean “previous app screen.” If URL-addressable screens, shareable conversation links, or route-level loading become requirements, React Router (or a router supplied by a framework) would be a better fit.

### Why not a global store?

The state is currently limited to a few screens. Passing a small number of callbacks and values from `App` is understandable and avoids a store dependency.

If many nested components need the same data, or state transitions become difficult to trace, Context can share stable app-wide values. A dedicated store such as Zustand or Redux is useful when there are many cross-screen updates, complex state transitions, or debugging requirements that justify it.

## 5. Main user flows

### Public landing → registration/login → dashboard

1. With no `gs_user` in local storage, `App` starts on the landing page.
2. The “Get started” action opens registration; the header login action opens login.
3. The form submits to `auth.register()` or `auth.login()` in `api.js`.
4. If the API succeeds, `enter()` stores the returned token and user, then switches to the dashboard.
5. Logout removes the token and user from local storage and returns the visitor to the public experience.

### Dashboard → assistant → answer

1. The user selects FarmSathi or NyayaSathi.
2. `App` stores which assistant was selected and displays `Chat`.
3. `Chat` trims the text, prevents empty or duplicate submissions, adds the user's message, and shows a loading state.
4. It calls `chat({ assistant, message, language })`.
5. On success, it appends the answer, evidence status, follow-up flag, and any source links.
6. On failure, it displays a localized error instead of pretending that the request succeeded.

The chat uses `useRef` and an effect to scroll to the latest message. The thread uses `aria-live="polite"` so assistive technology can be notified of conversation updates without unnecessarily interrupting the user.

### History

The history screen loads `history.list()` when it mounts. In demo mode, conversations are saved in local storage; with a working backend, history can come from the API.

## 6. Login and registration forms

Both login and registration are implemented with a real HTML `<form>` in `Auth`, not a clickable container styled to look like one.

### Why use a form tag?

The browser already understands form submission. A real form:

- Supports keyboard submission (including Enter in a field).
- Provides native required-field and input-type validation.
- Gives browsers and assistive technology a meaningful form structure.
- Provides a clear place to handle submission with `onSubmit`.
- Makes it easier to test the form using standard browser behavior.

A clickable `<div>` would need custom keyboard behavior, validation, focus management, and submit handling to recreate capabilities the browser provides natively.

### Field behavior

- Registration includes name, email, and password.
- Login includes email and password.
- Email inputs use `type="email"`; required fields use `required`.
- Passwords use `type="password"` and a minimum length of six characters.
- `autoComplete` hints distinguish account creation (`new-password`) from login (`current-password`).
- Visible `<label>` elements are associated with their inputs by nesting the input in the label.
- The form prevents a full-page browser navigation, awaits the API request, disables the submit button while busy, and announces errors with `role="alert"`.

The API still needs to enforce all security and account rules on the server. Browser validation improves usability; it is not a security boundary.

### Why not a form library?

The forms currently contain only a few fields and one submit action each. Native controlled inputs and browser validation keep the code small.

Formik, React Hook Form, or a schema validator can help when forms gain many fields, conditional rules, reusable field components, complex server validation, or wizard steps. Adding one now would create more abstraction than this simple form needs.

## 7. Localization

The `T` object in `App.jsx` contains parallel Hindi (`hi`) and English (`en`) labels and messages. Components receive the selected translation object as `t`; the chat request also receives the language code.

The selected language is stored as `gs_lang`, so it is restored after a reload. An effect updates `document.documentElement.lang`, which gives browsers and assistive technology the current document language.

### Why a dictionary instead of an i18n package?

There are currently two languages and a compact set of UI strings. A plain dictionary is easy to inspect and does not add a dependency.

An internationalization library becomes more valuable with many languages, plural rules, date/number formatting, interpolation, lazy-loaded translation files, translation workflows, or large sets of nested messages. At that point, the dictionary can be migrated rather than expanded indefinitely.

## 8. API layer and demo mode

Components call functions exported by `frontend/src/api.js`, rather than building URLs and fetch options in every screen. The module centralizes the API base URL, JSON headers, bearer token, error handling, and demo fallbacks.

### API base URL and development proxy

- `VITE_API_URL` sets an explicit API base URL.
- If it is empty, the frontend uses `/api`.
- Vite's development proxy forwards `/api` requests to `http://localhost:5000`.
- `frontend/.env.example` documents the example values. Do not put secret keys in frontend environment variables: values used by browser code are not private.

The proxy is a development convenience; production deployments need a matching API URL, reverse proxy, or same-origin backend arrangement.

### Demo fallback behavior

`VITE_USE_MOCK` defaults to enabled unless explicitly set to `"false"`. When enabled, the API helper uses demo behavior for requests that fail without an HTTP status (such as a network-level failure) or return HTTP 404. Other HTTP errors, including 401, 403, and 500, are surfaced instead of being silently represented as successful demo responses.

The mock chat is illustrative, not an AI model: it uses a small set of keyword checks and returns sample responses. Mock login/register return demo user data. Do not treat demo responses or demo tokens as production authentication or authoritative information.

Set `VITE_USE_MOCK=false` when verifying integration with live backend endpoints. Make sure the API base URL and backend are configured before doing so.

### Why use `fetch` instead of Axios?

The browser's built-in `fetch` can make these JSON requests and needs no additional package. The shared `req()` helper supplies common headers and token handling.

Axios is a reasonable alternative when an app needs features such as shared interceptors, extensive request cancellation patterns, or a project-wide Axios standard. There is no current need to add it for these few endpoints.

## 9. Browser storage and security

The frontend uses local storage for:

- `gs_lang`: language preference.
- `gs_user`: the minimal user object used to restore the UI.
- `gs_token`: the bearer token used by `api.js`.
- `gs_hist`: demo conversation history.

Local storage is convenient and survives page reloads, but it is accessible to JavaScript running on the page. A production system should carefully assess storing access tokens there because a cross-site scripting flaw could expose them. Depending on the backend's auth design, an `HttpOnly`, `Secure`, `SameSite` cookie can reduce JavaScript access to the session credential. Any change to cookie-based authentication needs coordinated backend and CSRF decisions; it should not be made only in the frontend.

The user object is for UI display, not authorization. The backend must validate the token and authorize every protected request. Clearing local storage on logout only clears this browser's UI session; server-side token expiry or revocation is a backend responsibility.

## 10. Visual and responsive design

The stylesheet uses CSS custom properties for the green/orange palette, surfaces, borders, and common radii. Landing, auth, dashboard, and chat have their own class groups, while buttons, focus outlines, and basic typography share common rules.

Responsive media queries change the two-column landing and auth layouts into single-column layouts, turn the dashboard sidebar into a compact horizontal navigation, and adjust card grids and spacing for narrow screens. A reduced-motion media query limits animation for users who request less motion.

### Why CSS artwork and emoji?

The landing scene is composed from CSS shapes, gradients, and text glyphs. This avoids an additional image dependency, keeps the artwork available offline, and makes the scene scale with its container.

The trade-off is that CSS shapes and emoji are less detailed and less visually consistent than a professionally illustrated asset. If the product needs a closer match to a specific illustration, use owned or properly licensed SVG/WebP artwork with appropriate responsive sizing and alternative text.

### Accessibility details

- Navigation uses a `<nav>` landmark and page regions use semantic elements such as `<main>`, `<section>`, `<aside>`, and `<footer>`.
- Form inputs have visible labels.
- Interactive elements are buttons or links rather than non-semantic clickable text.
- Focus-visible outlines are present for keyboard navigation.
- Error feedback uses `role="alert"`; chat updates use a polite live region.
- The document language follows the selected locale.
- Reduced-motion preferences are respected in CSS.

These are useful baseline practices, not a substitute for testing with keyboard-only navigation, screen readers, zoom, contrast tools, and real devices.

## 11. UI that is currently illustrative or limited

Some dashboard content is a visual starting point rather than a fully connected product feature:

- The “Recent activity” panel currently shows assistant categories and descriptions; it does not yet render the user's actual latest conversations.
- Settings, notification, profile, and voice-assistant concepts do not have complete settings/profile/voice workflows.
- The quick-link cards route to the relevant assistant rather than fetching a dedicated scheme, helpline, or notice service.
- The displayed helpline number is sample UI content and should be replaced with a verified number before release.
- The landing illustration is CSS artwork, not a photograph or detailed production illustration.
- Chat history retrieval depends on the configured backend; local persistence is intended for mock/demo use.

These limitations should be addressed before representing the shortcuts as live services or relying on them for real-world decisions.

## 12. Alternatives by requirement

| Current choice | Why it is used now | Consider an alternative when… |
| --- | --- | --- |
| React components and local state | Screens have interactive state and React is already in the project. | The project adopts a different framework or state becomes substantially more complex. |
| Vite SPA | Fast client-side development and a small production build. | Public content needs server rendering, route-level server logic, or SEO beyond static metadata. |
| JavaScript | Keeps the current app lightweight and avoids a type-system migration. | API contracts and the team need stronger compile-time guarantees; adopt TypeScript. |
| One shared CSS file | The number of screens and styles remains manageable. | Styles begin colliding or teams need stronger component-level isolation; consider CSS Modules. |
| Native HTML forms | A few fields with standard browser validation. | Forms gain complex rules, nested data, or multi-step workflows; consider React Hook Form/schema validation. |
| `fetch` | No extra dependency for a small JSON API layer. | The project standardizes on Axios or needs its interceptor ecosystem. |
| Local storage | Preferences and demo UI state persist through reloads. | Security/session requirements favor server-managed, HttpOnly cookie authentication. |
| Translation object | Two languages and a modest number of strings. | Localization grows to many languages, pluralization, or external translator workflows. |
| CSS illustration | No external art dependency and easy scaling. | The product requires a polished, branded, accessible illustration asset. |
| Conditional screen state | Few screens without required shareable URLs. | Deep links, browser history integration, or route-based loading are required; add a router. |

These are trade-offs, not universal rules. An alternative is useful when it solves a real project need, not simply because it is available.

## 13. Running and building the frontend

Run commands from the repository root with npm's `--prefix` option:

```bash
npm --prefix frontend run dev
npm --prefix frontend run build
npm --prefix frontend run preview
```

The development server uses port `5173` by default. A production build is written to `frontend/dist/`. The build verifies that Vite can transform and bundle the current frontend; it does not verify that the backend API is reachable or that authentication succeeds.

## 14. Suggested next steps as the product grows

1. Connect the dashboard's “Recent activity” panel to actual history data.
2. Replace sample helpline and demo copy with verified, reviewed product content.
3. Add tests for login/register validation, language switching, chat loading/error states, and history behavior.
4. Decide on a production session strategy with the backend team; review token storage and expiry.
5. Add route handling if screens need URLs that can be bookmarked or shared.
6. Consider TypeScript and API response types once endpoint contracts stabilize.
7. Test responsive layouts and accessibility with real devices and assistive technology.
8. Add a dedicated error/loading treatment for history instead of treating every history failure as an empty list.

