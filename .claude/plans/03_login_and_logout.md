Plan: Login and Logout (Step 03)

 Context

 Spendly currently lets visitors register (Step 02) but has no way to
 sign in.
 The /login route only renders a form, and /logout / /profile are raw
 placeholder stubs. This step adds session-based authentication: a user
 submits the login form, their credentials are verified against the
 users
 table, and on success their id and name are stored in Flask's session.
 Logout clears the session. The navbar becomes session-aware. After this
 step,
 the app knows who is logged in — the prerequisite for every
 authenticated
 feature that follows.

 Spec: .claude/specs/03_login-logout.md. Conventions: .claude/CLAUDE.md
 (Flask + SQLite only, parameterised queries, DB logic only in
 database/db.py,
 templates extend base.html, url_for() for all links, CSS variables
 only,
 port 5001).

 User decisions captured during planning:
 - Empty-field submissions show a distinct "All fields are required."
 message (mirroring register()); bad credentials show the generic
 "Invalid email or password."
 - An already-logged-in user hitting GET /login is redirected to
 /profile.

 No new files, no new pip packages, no CSS changes (existing .nav-links
 a /
 .nav-cta / .auth-error already use CSS variables).

 ---
 Implementation steps (bottom-up)

 1. database/db.py — add get_user_by_email(email)

 Place after create_user, before seed_db. Pure data-access:
 - db = get_db() (row_factory already sqlite3.Row).
 - Parameterised query: SELECT id, name, email, password_hash FROM users
 WHERE email = ? with (email,), then .fetchone().
 - db.close(), return the row (sqlite3.Row or None).

 Password verification stays out of db.py — get_user_by_email is a
 query,
 check_password_hash is auth policy and belongs in app.py. This honors
 the
 spec's exact file-change list and keeps db.py a pure data layer.

 2. app.py — imports + login() + logout()

 Imports:
 - Line 3: add session → from flask import Flask, render_template,
 request, redirect, url_for, abort, session
 - Add from werkzeug.security import check_password_hash
 - Line 5: extend to ..., create_user, get_user_by_email
 - abort already imported (Flask auto-returns 405 for unsupported
 methods; no manual handling needed).

 Replace login() (currently lines 47-49) — decorator becomes
 @app.route("/login", methods=["GET", "POST"]):
 if request.method == "GET":
     if session.get("user_id"):
         return redirect(url_for("profile"))      # already-logged-in
 guard
     return render_template("login.html")

 # POST
 email    = request.form.get("email", "").strip()
 password = request.form.get("password", "")      # do NOT strip
 password

 if not email or not password:
     return render_template("login.html", error="All fields are
 required.")

 user = get_user_by_email(email)
 if user is None or not check_password_hash(user["password_hash"],
 password):
     return render_template("login.html", error="Invalid email or
 password.")

 session["user_id"]   = user["id"]
 session["user_name"] = user["name"]
 return redirect(url_for("profile"))
 Only user_id (int) and user_name (str) ever enter the session — never
 the
 hash. check_password_hash(stored_hash, candidate) argument order
 matters.

 Replace logout() (currently lines 66-68), keep GET-only decorator:
 session.clear()
 return redirect(url_for("landing"))
 session.clear() is idempotent → repeat /logout with no session still
 redirects cleanly to /.

 Leave profile() and all other stubs untouched (CLAUDE.md: don't
 implement
 stubs outside the active step).

 3. templates/login.html — form action

 Line 20: action="/login" → action="{{ url_for('login') }}". The
 {% if error %} / .auth-error block already renders {{ error }} — no
 change.

 4. templates/base.html — session-aware navbar

 Replace the static nav-links block (lines 21-24) with a conditional,
 reusing
 existing CSS classes (no new CSS):
 <div class="nav-links">
     {% if session.user_id %}
         <a href="{{ url_for('profile') }}">{{ session.user_name }}</a>
         <a href="{{ url_for('logout') }}" class="nav-cta">Sign out</a>
     {% else %}
         <a href="{{ url_for('login') }}">Sign in</a>
         <a href="{{ url_for('register') }}" class="nav-cta">Get
 started</a>
     {% endif %}
 </div>
 session is auto-available in Jinja; session.user_id is falsy when
 unset.
 (Footer's hardcoded /terms /privacy links are pre-existing — out of
 scope.)

 ---
 Critical files

 - app.py — imports, login(), logout()
 - database/db.py — get_user_by_email()
 - templates/login.html — form action
 - templates/base.html — session-aware navbar

 ---
 Verification (port 5001)

 Run python app.py (auto-runs init_db() + seed_db(), seeding
 demo@spendly.com / demo123). Map to spec Definition of Done:

 1. GET /login renders the form, no traceback.
 2. Login demo@spendly.com / demo123 → 302 to /profile; navbar shows
 "Demo User" + "Sign out".
 3. Unknown email → form re-renders with "Invalid email or password.",
 no session.
 4. Wrong password → same generic error, no session.
 5. Empty field (curl -X POST -d "email=&password="
 http://localhost:5001/login)
 → "All fields are required."
 6. GET /logout while logged in → 302 to /; navbar reverts to logged-out
 links.
 7. Repeat /logout with no session → 302 to /, no error.
 8. Logged-out navbar shows "Sign in" / "Get started".
 9. Logged-in navbar shows user name + "Sign out".
 10. Already logged in + visit GET /login → 302 to /profile.
 11. Session cookie carries only user_id / user_name — never the hash
 (guaranteed by code path; only those two keys are ever assigned).

 Curl smoke:
 - curl -i -X POST -d "email=demo@spendly.com&password=demo123"
 http://localhost:5001/login → 302, Location: /profile, Set-Cookie:
 session=...
 - curl -i http://localhost:5001/logout → 302, Location: /