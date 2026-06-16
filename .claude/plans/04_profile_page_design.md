Here is Claude's plan:
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Implementation Plan: Profile Page (UI-only, hardcoded data)

 Context

 The /profile route in app.py:92-94 is currently a stub returning the
 plain string
 "Profile page — coming in Step 4". Per the canonical spec
 (.claude/specs/04_profile-page-design.md), this step builds the full
 profile UI with
 hardcoded data — no database queries (DB wiring is a later step).
 Building the UI in
 isolation lets the design be validated and leaves the template ready
 for backend
 connection later. The page must be auth-guarded, extend base.html,
 use only CSS
 variables (no hex in profile files), and keep all styles in a
 dedicated CSS file.

 Approach decisions

 - Category colors: reuse the 3 existing colored token families in
 style.css
 (--accent green, --accent-2 amber, --danger red) plus neutral tokens
 for "Other".
 No new palette tokens — style.css is NOT modified. Categories share
 colors across
 the 3 families (user-chosen trade-off; badges are less individually
 distinct but no hex
 is introduced and the spec's file list stays exact).
 - Progress-bar widths: use predefined width-bucket classes (.w-10 …
 .w-100) in
 profile.css and pick the nearest bucket in the template. This avoids
 inline style=
 attributes, which the spec forbids ("No inline styles").

 Files

 - Modify: app.py — replace the /profile stub (lines 92-94).
 - Create: templates/profile.html — full page, extends base.html.
 - Create: static/css/profile.css — page-specific styles, CSS
 variables only.
 - Reference only: templates/base.html (blocks + navbar already
 handle logged-in state).
 - NOT touched: database/db.py, static/css/style.css.

 ---
 Step 1 — app.py /profile view

 Replace lines 92-94. redirect, url_for, render_template, session are
 already
 imported (app.py:3). Single responsibility: auth guard → prepare
 hardcoded context → render.

 @app.route("/profile")
 def profile():
     if not session.get("user_id"):
         return redirect(url_for("login"))

     user = {
         "name": "Demo User",
         "email": "demo@spendly.com",
         "initials": "DU",
         "member_since": "January 2026",
     }
     stats = {
         "total_spent": "₹42,850",
         "transaction_count": 28,
         "top_category": "Food",
     }
     transactions = [
         {"date": "12 Jun 2026", "description": "Grocery run —
 BigBasket", "category": "Food", "amount": "₹2,340"},
         {"date": "10 Jun 2026", "description": "Metro card
 recharge", "category": "Transport", "amount": "₹500"},
         {"date": "08 Jun 2026", "description": "Electricity bill",
 "category": "Bills", "amount": "₹1,890"},
         {"date": "05 Jun 2026", "description": "Pharmacy",
 "category": "Health", "amount": "₹620"},
         {"date": "02 Jun 2026", "description": "Movie night",
 "category": "Entertainment", "amount": "₹900"},
     ]
     categories = [
         {"name": "Food", "total": "₹15,200", "pct": 36},
         {"name": "Bills", "total": "₹9,400", "pct": 22},
         {"name": "Transport", "total": "₹6,800", "pct": 16},
         {"name": "Shopping", "total": "₹5,950", "pct": 14},
         {"name": "Health", "total": "₹3,200", "pct": 8},
         {"name": "Entertainment", "total": "₹1,700", "pct": 4},
     ]
     return render_template(
         "profile.html",
         user=user, stats=stats, transactions=transactions,
 categories=categories,
     )

 ---
 Step 2 — templates/profile.html

 Extends base.html; links page CSS via {% block head %}; four
 sections in one
 <section class="profile-section"> wrapper (mirrors the auth-section
 pattern in
 login.html). Reuses existing classes: .auth-card, .feature-title,
 .feature-body,
 .hero-badge/.hero-badge-dot,
 .mock-stat-card/.mock-stat-value/.mock-stat-label.
 No <style>, no style= attributes, no hex.

 {% extends "base.html" %}
 {% block title %}Profile — Spendly{% endblock %}
 {% block head %}
 <link rel="stylesheet" href="{{ url_for('static',
 filename='css/profile.css') }}">
 {% endblock %}
 {% block content %}
 <section class="profile-section">
   <div class="profile-container">

     {# 1. User info card #}
     <div class="auth-card profile-user-card">
       <div class="profile-avatar">{{ user.initials }}</div>
       <div class="profile-user-meta">
         <h1 class="feature-title">{{ user.name }}</h1>
         <p class="feature-body">{{ user.email }}</p>
         <span class="hero-badge"><span 
 class="hero-badge-dot"></span>Member since {{ user.member_since
 }}</span>
       </div>
     </div>

     {# 2. Summary stats row #}
     <div class="profile-stats">
       <div class="mock-stat-card"><div class="mock-stat-label">Total
 spent</div><div class="mock-stat-value">{{ stats.total_spent
 }}</div></div>
       <div class="mock-stat-card"><div 
 class="mock-stat-label">Transactions</div><div 
 class="mock-stat-value">{{ stats.transaction_count }}</div></div>
       <div class="mock-stat-card"><div class="mock-stat-label">Top
 category</div><div class="mock-stat-value">{{ stats.top_category
 }}</div></div>
     </div>

     {# 3. Transaction history table #}
     <div class="auth-card">
       <h2 class="feature-title profile-block-title">Recent
 transactions</h2>
       <table class="profile-table">

 <thead><tr><th>Date</th><th>Description</th><th>Category</th><th 
 class="ta-right">Amount</th></tr></thead>
         <tbody>
           {% for tx in transactions %}
           <tr>
             <td>{{ tx.date }}</td>
             <td>{{ tx.description }}</td>
             <td><span class="category-badge {{ tx.category | lower
 }}">{{ tx.category }}</span></td>
             <td class="ta-right">{{ tx.amount }}</td>
           </tr>
           {% endfor %}
         </tbody>
       </table>
     </div>

     {# 4. Category breakdown #}
     <div class="auth-card">
       <h2 class="feature-title profile-block-title">Category
 breakdown</h2>
       <div class="cat-breakdown">
         {% for cat in categories %}
         <div class="cat-row">
           <div class="cat-row-head">
             <span class="category-badge {{ cat.name | lower }}">{{
 cat.name }}</span>
             <span class="cat-total">{{ cat.total }}</span>
           </div>
           <div class="cat-bar">
             <div class="cat-bar-fill {{ cat.name | lower }} w-{{
 (cat.pct / 10) | round | int * 10 }}"></div>
           </div>
         </div>
         {% endfor %}
       </div>
     </div>

   </div>
 </section>
 {% endblock %}

 {{ category | lower }} → food, transport, bills, health,
 entertainment,
 shopping, other (exact match to the 7 seed categories), mapping to
 badge color classes.

 ---
 Step 3 — static/css/profile.css (CSS variables only, no hex)

 Layout / cards / table / avatar:
 .profile-section { max-width: var(--max-width); margin: 0 auto;
 padding: 3rem 1.5rem; }
 .profile-container { display: flex; flex-direction: column; gap:
 1.5rem; }
 .profile-user-card { display: flex; align-items: center; gap:
 1.25rem; }
 .profile-avatar {
   width: 64px; height: 64px; border-radius: 50%;
   background: var(--accent-light); color: var(--accent);
   font-family: var(--font-display); font-size: 1.5rem;
   display: flex; align-items: center; justify-content: center;
 flex-shrink: 0;
 }
 .profile-block-title { margin-bottom: 1rem; }
 .profile-stats { display: grid; grid-template-columns: repeat(3,
 1fr); gap: 1rem; }
 .profile-table { width: 100%; border-collapse: collapse; }
 .profile-table th { text-align: left; font-size: 0.75rem; color:
 var(--ink-muted); font-weight: 600; padding: 0.6rem 0.75rem;
 border-bottom: 1px solid var(--border); }
 .profile-table td { padding: 0.75rem; color: var(--ink-soft);
 border-bottom: 1px solid var(--border-soft); font-size: 0.9rem; }
 .profile-table tr:last-child td { border-bottom: none; }
 .ta-right { text-align: right; }

 Category badges — reuse 3 existing token families (user decision):
 .category-badge { display: inline-block; padding: 0.2rem 0.6rem;
 border-radius: var(--radius-sm); font-size: 0.75rem; font-weight:
 600; }
 /* green family */
 .category-badge.food, .category-badge.bills            { background:
 var(--accent-light);    color: var(--accent); }
 /* amber family */
 .category-badge.transport, .category-badge.shopping    { background:
 var(--accent-2-light);  color: var(--accent-2); }
 /* red family */
 .category-badge.health, .category-badge.entertainment  { background:
 var(--danger-light);    color: var(--danger); }
 /* neutral */
 .category-badge.other                                  { background:
 var(--paper-warm);      color: var(--ink-muted); }

 Category breakdown bars (fill color matches the badge family) +
 width buckets:
 .cat-breakdown { display: flex; flex-direction: column; gap: 1rem; }
 .cat-row-head { display: flex; justify-content: space-between;
 align-items: center; margin-bottom: 0.4rem; }
 .cat-total { font-size: 0.85rem; font-weight: 600; color:
 var(--ink); }
 .cat-bar { width: 100%; height: 8px; background: var(--paper-warm);
 border-radius: var(--radius-sm); overflow: hidden; }
 .cat-bar-fill { height: 100%; border-radius: var(--radius-sm); }
 .cat-bar-fill.food, .cat-bar-fill.bills           { background:
 var(--accent); }
 .cat-bar-fill.transport, .cat-bar-fill.shopping   { background:
 var(--accent-2); }
 .cat-bar-fill.health, .cat-bar-fill.entertainment { background:
 var(--danger); }
 .cat-bar-fill.other                               { background:
 var(--ink-muted); }
 .w-0{width:0} .w-10{width:10%} .w-20{width:20%} .w-30{width:30%}
 .w-40{width:40%}
 .w-50{width:50%} .w-60{width:60%} .w-70{width:70%} .w-80{width:80%}
 .w-90{width:90%} .w-100{width:100%}

 @media (max-width: 768px) {
   .profile-stats { grid-template-columns: 1fr; }
   .profile-user-card { flex-direction: column; text-align: center; }
 }

 ---
 Verification (manual, against each Definition-of-Done item)

 Run python app.py (boots on port 5001; auto-runs init_db() +
 seed_db()).

 1. Logged out → /login: curl -i http://localhost:5001/profile →
 expect 302 +
 Location: /login.
 2. Logged in → 200: sign in at /login with seeded demo@spendly.com /
 demo123,
 then visit /profile → HTTP 200, full page renders (not a plain
 string).
 3. User info card: shows "Demo User", "demo@spendly.com", avatar
 "DU", member-since pill.
 4. ≥3 summary stats: three .mock-stat-cards (Total spent,
 Transactions, Top category).
 5. Transaction table ≥3 rows: 5 hardcoded rows with date /
 description / category badge / amount.
 6. Category breakdown ≥3: 6 rows with colored badges + progress bars
 of differing widths.
 7. Navbar logged-in state: username link + "Sign out" (handled by
 base.html, set at app.py:67-68).
 8. No hex in profile files:
 grep -nE '#[0-9a-fA-F]{3,6}' templates/profile.html
 static/css/profile.css → zero matches.
 9. Regression: pytest passes (no existing tests broken).