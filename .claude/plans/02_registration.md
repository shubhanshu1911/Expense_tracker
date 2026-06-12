Plan: Step 2 — User Registration

 Context

 The GET /register route and register.html template already exist as
 stubs. This step wires up the POST /register handler so new users can
 create an account. The form validates input, hashes the password via
 werkzeug, inserts a row into the users table, and redirects to /login
 on success. Validation failures re-render the form with an inline
 error= variable (consistent with login.html's existing pattern — no
 flash infrastructure needed).

 app.secret_key is set here even though sessions aren't used until Step
 3, as it's a prerequisite for session management.

 ---
 Implementation Order

 1. database/db.py — Add create_user()

 Add after seed_db(). Follow the exact existing pattern: get_db() →
 db.execute() → db.commit() → db.close().

 def create_user(name, email, password):
     password_hash = generate_password_hash(password)
     db = get_db()
     db.execute(
         "INSERT INTO users (name, email, password_hash) VALUES (?, ?,
 ?)",
         (name, email, password_hash),
     )
     db.commit()
     user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
     db.close()
     return user_id

 - Do NOT catch sqlite3.IntegrityError here — let it bubble up to the
 route.
 - generate_password_hash is already imported at the top of the file.
 - No new imports needed (sqlite3 is already imported).

 ---
 2. app.py — Upgrade register() route

 Extend the Flask import line:
 from flask import Flask, render_template, request, redirect, url_for,
 abort

 Add import sqlite3 as a top-level import.

 Extend the db import:
 from database.db import get_db, init_db, seed_db, create_user

 Set secret_key immediately after app = Flask(__name__):
 app.secret_key = "spendly-dev-secret-key"

 Replace the register() route:
 @app.route("/register", methods=["GET", "POST"])
 def register():
     if request.method == "GET":
         return render_template("register.html")

     name = request.form.get("name", "").strip()
     email = request.form.get("email", "").strip()
     password = request.form.get("password", "")
     confirm_password = request.form.get("confirm_password", "")

     if not name or not email or not password or not confirm_password:
         return render_template("register.html", error="All fields are
 required.")

     if password != confirm_password:
         return render_template("register.html", error="Passwords do not
 match.")

     if len(password) < 8:
         return render_template("register.html", error="Password must be
 at least 8 characters.")

     try:
         create_user(name, email, password)
     except sqlite3.IntegrityError:
         return render_template("register.html", error="Email already
 registered.")

     return redirect(url_for("login"))

 Validation order: empty fields → password match → min length → DB
 uniqueness. No DB write happens until all client-side checks pass.

 ---
 3. templates/register.html — Wire up the form

 Fix hardcoded action (line 20):
 <form method="POST" action="{{ url_for('register') }}">

 Add confirm_password field — insert after the password form-group,
 before the submit button:
 <div class="form-group">
     <label for="confirm_password">Confirm password</label>
     <input type="password" id="confirm_password" 
 name="confirm_password"
            class="form-input" placeholder="Repeat your password"
            required>
 </div>

 The existing {% if error %}<div class="auth-error">{{ error }}</div>{%
 endif %} block remains unchanged.

 ---
 4. static/css/style.css — Fix hardcoded hex in .auth-error

 The .auth-error rule has a hardcoded #f5c6c2 border, violating the
 CSS-variables-only constraint.

 Add to :root block alongside --danger and --danger-light:
 --danger-border: #f5c6c2;

 Update the .auth-error border line:
 border: 1px solid var(--danger-border);

 ---
 Files Changed

 ┌─────────────────────────┬─────────────────────────────────────────┐
 │          File           │                 Change                  │
 ├─────────────────────────┼─────────────────────────────────────────┤
 │ database/db.py          │ Add create_user()                       │
 ├─────────────────────────┼─────────────────────────────────────────┤
 │ app.py                  │ Add imports, secret_key, upgrade        │
 │                         │ register()                              │
 ├─────────────────────────┼─────────────────────────────────────────┤
 │ templates/register.html │ Fix action, add confirm_password field  │
 ├─────────────────────────┼─────────────────────────────────────────┤
 │ static/css/style.css    │ Add --danger-border var, remove         │
 │                         │ hardcoded hex                           │
 └─────────────────────────┴─────────────────────────────────────────┘

 Files Created

 None.

 ---
 Verification

 1. Start the app: python app.py
 2. Visit http://localhost:5001/register
 3. Submit with all empty fields → inline error "All fields are
 required."
 4. Submit with mismatched passwords → "Passwords do not match."
 5. Submit with password < 8 chars → "Password must be at least 8
 characters."
 6. Submit valid data → redirects to /login
 7. Resubmit same email → "Email already registered."
 8. Inspect spendly.db (sqlite3 spendly.db "SELECT email, password_hash
 FROM users") — confirm hash, not plaintext
 9. Confirm GET /register still works cleanly with no errors