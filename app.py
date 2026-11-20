import customtkinter as ctk, tkinter as tk, sqlite3, csv, webbrowser, threading, subprocess, re, socket, shutil
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
import engine

DB = "shawon_client_finder_pro.db"
BG = "#070b16"; SIDE = "#0c1224"; CARD = "#111a31"; CARD2 = "#18243f"; LINE = "#243158"
TXT = "#f2f5ff"; MUT = "#8d9bbd"; PUR = "#7c5cff"; CYA = "#22d3ee"; GRN = "#10d9a0"; ORG = "#ff9f43"; RED = "#ff5c7a"; BLU = "#3b82f6"
SERVICES = ["Logo Design", "Branding", "Business Card Design", "Website Design", "E-commerce Website", "Android App Development", "App UI/UX", "Other"]
STATUSES = ["New", "Researching", "Ready to Contact", "Contacted", "Replied", "Interested", "Follow-up", "Won", "Not a Fit"]
EMAIL_ST = ["Not checked", "Format valid", "Domain resolves", "MX record found", "Invalid / no MX", "Unknown"]
KEYS = ["business", "contact", "email", "website", "phone", "country", "city", "service", "source_url", "need_signal", "status", "followup", "email_status", "notes"]
F = lambda s=13, w="normal": ctk.CTkFont("Segoe UI", s, w)

def lt(c, k=28):
    r, g, b = [int(c[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(min(255, x + k) for x in (r, g, b))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark"); self.title("SHAWON AI CLIENT FINDER PRO | v6.0"); self.geometry("1360x840"); self.minsize(1180, 740)
        self.configure(fg_color=BG)
        self.conn = sqlite3.connect(DB); self.conn.row_factory = sqlite3.Row
        self.conn.execute("""CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY AUTOINCREMENT, business TEXT NOT NULL, contact TEXT, email TEXT,
          website TEXT, phone TEXT, country TEXT, city TEXT, service TEXT, source_url TEXT, need_signal TEXT, status TEXT, score INTEGER,
          score_reason TEXT, followup TEXT, email_status TEXT, notes TEXT, created_at TEXT, updated_at TEXT)"""); self.conn.commit()
        self.selected = None; self.found = {}; self.vars = {}
        st = ttk.Style(); st.theme_use("clam")
        st.configure("T.Treeview", background=CARD, fieldbackground=CARD, foreground=TXT, rowheight=38, borderwidth=0, font=("Segoe UI", 10))
        st.configure("T.Treeview.Heading", background=CARD2, foreground=MUT, relief="flat", font=("Segoe UI", 9, "bold"), padding=9)
        st.map("T.Treeview", background=[("selected", "#2b3a7a")]); st.map("T.Treeview.Heading", background=[("active", CARD2)])
        self.side = ctk.CTkFrame(self, width=232, corner_radius=0, fg_color=SIDE); self.side.pack(side="left", fill="y"); self.side.pack_propagate(False)
        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=BG); self.main.pack(side="left", fill="both", expand=True)
        self.pages = {k: ctk.CTkFrame(self.main, fg_color=BG, corner_radius=0) for k in ("dash", "auto", "leads", "set")}
        self.build_side(); self.build_dash(); self.build_auto(); self.build_leads(); self.build_settings()
        self.show("dash"); self.refresh()

    # ---------- helpers ----------
    def card(self, p, **kw): return ctk.CTkFrame(p, fg_color=CARD, corner_radius=18, border_width=1, border_color=LINE, **kw)
    def lab(self, p, t, s=12, c=MUT, w="normal"): return ctk.CTkLabel(p, text=t, font=F(s, w), text_color=c)
    def btn(self, p, t, cmd, c=PUR, fg="white", **kw):
        kw.setdefault("height", 40)
        return ctk.CTkButton(p, text=t, command=cmd, fg_color=c, hover_color=lt(c), text_color=fg, corner_radius=12, font=F(12, "bold"), **kw)
    def ent(self, p, var, ph="", w=200): return ctk.CTkEntry(p, textvariable=var, placeholder_text=ph, height=38, width=w, corner_radius=10, fg_color=CARD2, border_color=LINE, text_color=TXT)
    def menu(self, p, var, vals, w=200): return ctk.CTkOptionMenu(p, variable=var, values=vals, width=w, height=38, corner_radius=10, fg_color=CARD2, button_color=PUR, button_hover_color=lt(PUR), dropdown_fg_color=CARD2)
    def table(self, p, cols, widths):
        t = ttk.Treeview(p, columns=cols, show="headings", style="T.Treeview", selectmode="extended")
        for c, w in zip(cols, widths): t.heading(c, text=c.upper()); t.column(c, width=w, anchor="w")
        t.tag_configure("hi", foreground=GRN); t.tag_configure("mid", foreground=ORG); t.tag_configure("lo", foreground=MUT); return t
    def bg(self, fn, done):
        def run():
            try: r, err = fn(), None
            except Exception as e: r, err = None, str(e)
            self.after(0, lambda: done(r, err))
        threading.Thread(target=run, daemon=True).start()
    def show(self, k):
        for n, f in self.pages.items(): f.pack_forget()
        self.pages[k].pack(fill="both", expand=True)
        for n, b in self.nav.items(): b.configure(fg_color=PUR if n == k else "transparent", text_color="white" if n == k else MUT)

    def build_side(self):
        s = self.side
        ctk.CTkLabel(s, text="✦", font=F(34, "bold"), text_color=ORG).pack(anchor="w", padx=24, pady=(26, 0))
        self.lab(s, "SHAWON", 22, TXT, "bold").pack(anchor="w", padx=24)
        self.lab(s, "AI CLIENT FINDER PRO", 10, CYA, "bold").pack(anchor="w", padx=24, pady=(0, 28))
        self.nav = {}
        for k, t in [("dash", "▦   Dashboard"), ("auto", "⚡   Auto Finder"), ("leads", "☰   My Leads / CRM"), ("set", "⚙   Settings")]:
            b = ctk.CTkButton(s, text=t, anchor="w", height=46, corner_radius=12, fg_color="transparent", hover_color=CARD2, text_color=MUT, font=F(13, "bold"), command=lambda k=k: self.show(k))
            b.pack(fill="x", padx=16, pady=3); self.nav[k] = b
        box = ctk.CTkFrame(s, fg_color=CARD, corner_radius=16, border_width=1, border_color=LINE); box.pack(side="bottom", fill="x", padx=16, pady=20)
        self.lab(box, "100% FREE MODE", 11, GRN, "bold").pack(anchor="w", padx=16, pady=(14, 2))
        self.lab(box, "No credit card.\nNo paid API needed.", 10, MUT).pack(anchor="w", padx=16, pady=(0, 14))

    def head(self, p, t, sub):
        self.lab(p, t, 28, TXT, "bold").pack(anchor="w", padx=30, pady=(26, 0)); self.lab(p, sub, 12).pack(anchor="w", padx=30, pady=(2, 14))

    # ---------- Dashboard ----------
    def build_dash(self):
        p = self.pages["dash"]; self.head(p, "Welcome back, Shawon 👋", "Find real businesses, audit their weak spots, and win more clients.")
        row = ctk.CTkFrame(p, fg_color="transparent"); row.pack(fill="x", padx=24); self.st = {}
        for k, t, c in [("total", "TOTAL LEADS", BLU), ("high", "HIGH POTENTIAL", GRN), ("follow", "FOLLOW-UPS DUE", PUR), ("won", "WON CLIENTS", ORG)]:
            cd = self.card(row); cd.pack(side="left", expand=True, fill="x", padx=6)
            ctk.CTkFrame(cd, height=4, fg_color=c, corner_radius=4).pack(fill="x", padx=20, pady=(16, 0))
            self.lab(cd, t, 10, MUT, "bold").pack(anchor="w", padx=20, pady=(10, 0))
            self.st[k] = self.lab(cd, "0", 38, TXT, "bold"); self.st[k].pack(anchor="w", padx=20, pady=(0, 14))
        q = ctk.CTkFrame(p, fg_color="transparent"); q.pack(fill="x", padx=30, pady=18)
        self.btn(q, "⚡  Find new clients", lambda: self.show("auto"), PUR, width=190).pack(side="left", padx=(0, 10))
        self.btn(q, "＋  Add lead manually", lambda: (self.clear(), self.show("leads")), BLU, width=190).pack(side="left", padx=10)
        self.btn(q, "⇩  Export CSV", self.export_csv, GRN, fg="#04251c", width=150).pack(side="left", padx=10)
        mid = ctk.CTkFrame(p, fg_color="transparent"); mid.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        l = self.card(mid); l.pack(side="left", fill="both", expand=True, padx=6)
        self.lab(l, "PIPELINE", 12, TXT, "bold").pack(anchor="w", padx=22, pady=(18, 8)); self.pipe = {}
        for s_ in STATUSES:
            r = ctk.CTkFrame(l, fg_color="transparent"); r.pack(fill="x", padx=22, pady=3)
            self.lab(r, s_, 11).pack(side="left"); c = self.lab(r, "0", 11, TXT, "bold"); c.pack(side="right")
            pb = ctk.CTkProgressBar(r, width=230, height=8, progress_color=PUR, fg_color=CARD2); pb.pack(side="right", padx=12); pb.set(0); self.pipe[s_] = (pb, c)
        r_ = self.card(mid); r_.pack(side="left", fill="both", expand=True, padx=6)
        self.lab(r_, "TOP LEADS", 12, TXT, "bold").pack(anchor="w", padx=22, pady=(18, 8)); self.top = []
        for _ in range(7):
            x = self.lab(r_, "—", 12, MUT); x.pack(anchor="w", padx=22, pady=5); self.top.append(x)

    # ---------- Auto Finder ----------
    def build_auto(self):
        p = self.pages["auto"]; self.head(p, "International Client Finder", "Find business prospects and search for public project requests in your target market.")
        c = self.card(p); c.pack(fill="x", padx=30)
        self.av = {"cat": tk.StringVar(value="marketing agency"), "city": tk.StringVar(value="New York"), "country": tk.StringVar(value="United States")}
        self.market_presets = {
            "United States": ("New York", "United States"), "United Kingdom": ("London", "United Kingdom"),
            "Canada": ("Toronto", "Canada"), "Australia": ("Sydney", "Australia"),
            "Germany": ("Berlin", "Germany"), "France": ("Paris", "France"),
            "Netherlands": ("Amsterdam", "Netherlands"), "Switzerland": ("Zurich", "Switzerland"),
            "Sweden": ("Stockholm", "Sweden"), "Norway": ("Oslo", "Norway"),
            "Denmark": ("Copenhagen", "Denmark"), "Ireland": ("Dublin", "Ireland"),
            "New Zealand": ("Auckland", "New Zealand"), "Singapore": ("Singapore", "Singapore")
        }
        g = ctk.CTkFrame(c, fg_color="transparent"); g.pack(fill="x", padx=18, pady=16)
        self.lab(g, "BUSINESS TYPE", 9, MUT, "bold").grid(row=0, column=0, sticky="w", padx=6)
        self.menu(g, self.av["cat"], list(engine.CATS), 205).grid(row=1, column=0, padx=6, pady=(4, 0))
        self.lab(g, "TARGET MARKET", 9, MUT, "bold").grid(row=0, column=1, sticky="w", padx=6)
        self.market_var = tk.StringVar(value="United States")
        self.menu(g, self.market_var, list(self.market_presets), 180).grid(row=1, column=1, padx=6, pady=(4, 0))
        self.lab(g, "CITY", 9, MUT, "bold").grid(row=0, column=2, sticky="w", padx=6)
        self.ent(g, self.av["city"], "e.g. New York", 170).grid(row=1, column=2, padx=6, pady=(4, 0))
        self.lab(g, "COUNTRY", 9, MUT, "bold").grid(row=0, column=3, sticky="w", padx=6)
        self.ent(g, self.av["country"], "e.g. United States", 170).grid(row=1, column=3, padx=6, pady=(4, 0))
        self.market_var.trace_add("write", self.apply_market)
        self.btn(g, "🔎 FIND BUSINESSES", self.auto_search, PUR, width=150, height=42).grid(row=1, column=4, padx=8)
        service_row = ctk.CTkFrame(p, fg_color="transparent"); service_row.pack(fill="x", padx=30, pady=(0, 6))
        self.lab(service_row, "SERVICE YOU OFFER", 9, MUT, "bold").pack(side="left", padx=(4, 10))
        self.service_var = tk.StringVar(value="Logo & Branding")
        self.menu(service_row, self.service_var,
                  ["Logo & Branding", "Website Design", "App Development"], 205).pack(side="left")
        self.lab(service_row, "Choose a service, then search for businesses or public project requests.", 10, MUT).pack(side="left", padx=12)
        bar = ctk.CTkFrame(p, fg_color="transparent"); bar.pack(fill="x", padx=30, pady=8)
        self.btn(bar, "🛠 Audit websites", self.auto_audit, BLU, width=145).pack(side="left", padx=(0, 6))
        self.btn(bar, "＋ Save to CRM", self.auto_save, GRN, fg="#04251c", width=130).pack(side="left", padx=6)
        self.btn(bar, "Google: Project Requests", self.open_google_opportunities, CARD2, width=190).pack(side="left", padx=6)
        self.btn(bar, "Bing: Project Requests", self.open_bing_opportunities, CARD2, width=180).pack(side="left", padx=6)
        self.astatus = self.lab(bar, "Business listings are prospects; project-request searches reveal stronger buying intent.", 9, CYA, "bold"); self.astatus.pack(side="left", padx=6)
        self.prog = ctk.CTkProgressBar(bar, width=160, height=8, mode="indeterminate", progress_color=CYA, fg_color=CARD2); self.prog.pack(side="right")
        self.atree = self.table(p, ("name", "website", "phone", "email", "signals"), [220, 190, 130, 190, 470]); self.atree.pack(fill="both", expand=True, padx=30, pady=(0, 24))

    def apply_market(self, *_):
        city, country = self.market_presets.get(self.market_var.get(), ("", ""))
        if city:
            self.av["city"].set(city)
            self.av["country"].set(country)

    def _market_text(self):
        return f"{self.av['city'].get().strip()}, {self.av['country'].get().strip()}"

    def _opportunity_queries(self):
        service = self.service_var.get()
        market = self._market_text()
        if service == "Logo & Branding":
            terms = [
                '"looking for a logo designer"',
                '"need a logo designer" OR "need a new logo"',
                '"brand identity design" project OR "rebranding" designer',
                '"logo design" RFP OR "brand identity" RFP'
            ]
        elif service == "Website Design":
            terms = [
                '"looking for a web designer"',
                '"need a website" OR "website redesign" project',
                '"web design" RFP OR "website development" RFP',
                '"hire a website designer" OR "web design project"'
            ]
        else:
            terms = [
                '"looking for an app developer"',
                '"mobile app development" project OR "need an app"',
                '"app development" RFP OR "mobile application" RFP',
                '"hire an app developer" OR "iOS Android app project"'
            ]
        return [f'{term} "{market}"' for term in terms]

    def _open_opportunity_search(self, engine_name="google"):
        import urllib.parse
        queries = self._opportunity_queries()
        # Open a focused search set in separate tabs; the user reviews and verifies results.
        base = "https://www.google.com/search?q=" if engine_name == "google" else "https://www.bing.com/search?q="
        for query in queries:
            webbrowser.open(base + urllib.parse.quote(query))
        self.astatus.configure(text=f"Opened {len(queries)} {engine_name.title()} searches for {self.service_var.get()}.")

    def open_google_opportunities(self):
        self._open_opportunity_search("google")

    def open_bing_opportunities(self):
        self._open_opportunity_search("bing")

    def _discovery_query(self):
        import urllib.parse
        v = {k: x.get().strip() for k, x in self.av.items()}
        return urllib.parse.quote(f'"{v["cat"]}" businesses in {v["city"]}, {v["country"]} official website contact')

    def open_google_discovery(self):
        webbrowser.open("https://www.google.com/search?q=" + self._discovery_query())

    def open_bing_discovery(self):
        webbrowser.open("https://www.bing.com/search?q=" + self._discovery_query())

    def auto_search(self):
        v = {k: x.get().strip() for k, x in self.av.items()}
        if not v["city"] or not v["country"]:
            messagebox.showwarning("Target market", "Enter a city and country first.")
            return
        self.astatus.configure(text=f"Searching public map listings: {v['city']}, {v['country']}..."); self.prog.start()
        def done(rows, err):
            self.prog.stop()
            if err: self.astatus.configure(text="Search failed."); messagebox.showerror("Search failed", err); return
            self.atree.delete(*self.atree.get_children()); self.found = {}; rows.sort(key=lambda r: bool(r["website"]))
            for i, r in enumerate(rows):
                r["signals"] = "" if r["website"] else "No website found"; self.found[str(i)] = r
                self.atree.insert("", "end", iid=str(i), values=(r["name"], r["website"], r["phone"], r["email"], r["signals"]))
            self.astatus.configure(text=f"{len(rows)} public listings found. Use Google/Bing for wider discovery.")
        self.bg(lambda: engine.osm(v["cat"], v["city"], v["country"]), done)

    def _audit_rows(self, ids, cb=None):
        self.astatus.configure(text=f"Auditing {len(ids)} websites..."); self.prog.start()
        def work():
            for i in ids:
                r = self.found[i]; a = engine.audit(r["website"]); r["signals"] = " | ".join(a["signals"]); r["email"] = r["email"] or (a["emails"][0] if a["emails"] else "")
        def done(_, err):
            self.prog.stop()
            for i in ids: r = self.found[i]; self.atree.item(i, values=(r["name"], r["website"], r["phone"], r["email"], r["signals"]))
            self.astatus.configure(text="Audit complete.")
            if cb: cb()
        self.bg(work, done)

    def auto_audit(self):
        ids = self.atree.selection()
        if ids: self._audit_rows(ids)
        else: messagebox.showinfo("Select", "Select one or more businesses first.")

    def auto_save(self):
        ids = self.atree.selection()
        if not ids: messagebox.showinfo("Select", "Select one or more businesses first."); return
        def save():
            added = 0
            for i in ids:
                r = self.found[i]
                d = dict(business=r["name"], contact="", email=r["email"], website=r["website"], phone=r["phone"], country=self.av["country"].get(), city=self.av["city"].get(),
                         service=self.service_var.get(), source_url=r["src"],
                         need_signal=("Business directory listing only; buying intent not confirmed. " + (r["signals"] or "No specific need signal checked.")),
                         status="Researching", followup="",
                         email_status="Format valid" if r["email"] else "Not checked", notes=r["address"])
                if self.conn.execute("SELECT id FROM leads WHERE lower(business)=lower(?) AND lower(website)=lower(?)", (d["business"], d["website"])).fetchone(): continue
                self.insert(d); added += 1
            self.conn.commit(); self.refresh(); self.astatus.configure(text=f"Saved {added} new leads to CRM.")
        todo = [i for i in ids if self.found[i]["website"] and not self.found[i]["signals"]]
        self._audit_rows(todo, save) if todo else save()

    # ---------- CRM ----------
    def build_leads(self):
        p = self.pages["leads"]; self.head(p, "My Leads / CRM", "Track every business from first research to a won client.")
        body = ctk.CTkFrame(p, fg_color="transparent"); body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        left = ctk.CTkFrame(body, fg_color="transparent"); left.pack(side="left", fill="both", expand=True, padx=6)
        tb = ctk.CTkFrame(left, fg_color="transparent"); tb.pack(fill="x", pady=(0, 10)); self.filter = tk.StringVar()
        self.ent(tb, self.filter, "Search leads...", 300).pack(side="left"); self.filter.trace_add("write", lambda *a: self.refresh())
        self.btn(tb, "Import CSV", self.import_csv, CARD2, width=110, height=38).pack(side="right", padx=(8, 0)); self.btn(tb, "Export CSV", self.export_csv, CARD2, width=110, height=38).pack(side="right")
        self.tree = self.table(left, ("business", "service", "city", "score", "status", "followup"), [190, 130, 90, 80, 135, 100]); self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.select)
        self.why = self.lab(left, "Select a lead to see its score and evidence.", 11, MUT); self.why.configure(wraplength=700, justify="left"); self.why.pack(anchor="w", pady=10)
        form = ctk.CTkScrollableFrame(body, width=370, fg_color=CARD, corner_radius=18, border_width=1, border_color=LINE); form.pack(side="left", fill="y", padx=6)
        self.lab(form, "LEAD DETAILS", 12, TXT, "bold").pack(anchor="w", pady=(6, 6))
        for k, t in [("business", "Business name *"), ("contact", "Contact person"), ("email", "Public business email"), ("website", "Website"), ("phone", "Public phone"), ("country", "Country"), ("city", "City"), ("source_url", "Source URL"), ("need_signal", "Evidence / possible need"), ("followup", "Follow-up date (YYYY-MM-DD)")]:
            self.vars[k] = tk.StringVar(); self.lab(form, t, 10, MUT, "bold").pack(anchor="w", pady=(6, 1)); self.ent(form, self.vars[k], "", 320).pack(fill="x")
        for k, t, v in [("service", "Service", SERVICES), ("status", "Status", STATUSES), ("email_status", "Email status", EMAIL_ST)]:
            self.vars[k] = tk.StringVar(value=v[0]); self.lab(form, t, 10, MUT, "bold").pack(anchor="w", pady=(6, 1)); self.menu(form, self.vars[k], v, 320).pack(fill="x")
        self.lab(form, "Notes", 10, MUT, "bold").pack(anchor="w", pady=(6, 1)); self.notes = ctk.CTkTextbox(form, height=70, fg_color=CARD2, corner_radius=10); self.notes.pack(fill="x")
        r = ctk.CTkFrame(form, fg_color="transparent"); r.pack(fill="x", pady=(12, 4))
        for t, c, f in [("SAVE", PUR, self.save), ("CLEAR", CARD2, self.clear), ("DELETE", RED, self.delete)]: self.btn(r, t, f, c, width=96).pack(side="left", padx=3, expand=True)
        for t, c, f, fg in [("🛠  Audit website", BLU, self.audit_current, "white"), ("✨  AI pitch message", ORG, self.pitch_current, "#2a1600"), ("✉  Check email domain", CYA, self.verify_email, "#04222a"), ("↗  Open website", CARD2, self.open_site, "white")]:
            self.btn(form, t, f, c, fg=fg).pack(fill="x", pady=3)

    def formdata(self):
        d = {k: v.get().strip() for k, v in self.vars.items()}; d["notes"] = self.notes.get("1.0", "end").strip(); return d

    def score(self, d):
        pts = []; n = 0
        for cond, v, t in [(d["business"], 10, "Business identified"), (d["website"], 8, "Website available"),
                           (d["source_url"], 8, "Source link recorded"),
                           (d["service"] and d["service"] != "Other", 8, "Service selected"),
                           (d["country"], 4, "Target country"), (d["phone"], 4, "Public phone")]:
            if cond: n += v; pts.append(f"{t} (+{v})")
        evidence = (d.get("need_signal") or "").lower()
        intent_terms = ("looking for", "need a", "need an", "seeking", "hiring", "request for proposal",
                        "rfp", "project brief", "redesign project", "rebrand", "developer wanted",
                        "designer wanted", "quote request", "requesting proposals")
        if any(term in evidence for term in intent_terms):
            n += 38; pts.append("Explicit public buying-intent phrase (+38)")
        elif any(term in evidence for term in ("no viewport", "outdated", "missing title", "website unreachable",
                                                "no website found", "placeholder")):
            n += 12; pts.append("Possible website improvement signal (+12; needs manual review)")
        elif evidence and "buying intent not confirmed" not in evidence:
            n += 5; pts.append("General research note (+5)")
        if d["email"]:
            ok = d["email_status"] in ("Format valid", "Domain resolves", "MX record found")
            n += 10 if ok else 3
            pts.append("Email domain checks passed (+10)" if ok else "Email present but unverified (+3)")
        return min(n, 100), "; ".join(pts)

    def insert(self, d):
        sc, rs = self.score(d); now = datetime.now().isoformat(timespec="seconds")
        self.conn.execute("INSERT INTO leads(" + ",".join(KEYS) + ",score,score_reason,created_at,updated_at) VALUES(" + ",".join("?" * (len(KEYS) + 4)) + ")", [d.get(k, "") for k in KEYS] + [sc, rs, now, now])

    def save(self):
        d = self.formdata()
        if not d["business"]: messagebox.showwarning("Required", "Business name is required."); return
        if self.selected:
            sc, rs = self.score(d)
            self.conn.execute("UPDATE leads SET " + ",".join(k + "=?" for k in KEYS) + ",score=?,score_reason=?,updated_at=? WHERE id=?", [d[k] for k in KEYS] + [sc, rs, datetime.now().isoformat(timespec="seconds"), self.selected])
        else: self.insert(d)
        self.conn.commit(); self.clear(); self.refresh()

    def refresh(self):
        if not hasattr(self, "tree"): return
        self.tree.delete(*self.tree.get_children()); q = f"%{self.filter.get().strip()}%"
        for r in self.conn.execute("SELECT * FROM leads WHERE business LIKE ? OR email LIKE ? OR city LIKE ? OR service LIKE ? ORDER BY score DESC,id DESC", (q,) * 4):
            self.tree.insert("", "end", iid=str(r["id"]), values=(r["business"], r["service"], r["city"], r["score"], r["status"], r["followup"]), tags=("hi" if r["score"] >= 75 else "mid" if r["score"] >= 50 else "lo",))
        a = self.conn.execute("SELECT * FROM leads").fetchall(); today = date.today().isoformat()
        for k, v in [("total", len(a)), ("high", sum(r["score"] >= 75 for r in a)), ("follow", sum(bool(r["followup"]) and r["followup"] <= today and r["status"] not in ("Won", "Not a Fit") for r in a)), ("won", sum(r["status"] == "Won" for r in a))]: self.st[k].configure(text=str(v))
        for s_, (pb, c) in self.pipe.items(): n = sum(r["status"] == s_ for r in a); c.configure(text=str(n)); pb.set(n / max(1, len(a)))
        top = sorted(a, key=lambda r: -r["score"])[:7]
        for i, x in enumerate(self.top): x.configure(text=f"{top[i]['score']:>3}   {top[i]['business']}  ·  {top[i]['service']}" if i < len(top) else "—", text_color=GRN if i < len(top) and top[i]["score"] >= 75 else MUT)

    def select(self, e=None):
        s = self.tree.selection()
        if not s: return
        self.selected = int(s[0]); r = self.conn.execute("SELECT * FROM leads WHERE id=?", (self.selected,)).fetchone()
        for k in self.vars: self.vars[k].set(r[k] or "")
        self.notes.delete("1.0", "end"); self.notes.insert("1.0", r["notes"] or "")
        self.why.configure(text=f"Research score: {r['score']}/100   ·   {r['score_reason']}\nThe score ranks research completeness. It does not prove buying intent.")

    def clear(self):
        self.selected = None
        for v in self.vars.values(): v.set("")
        self.vars["service"].set(SERVICES[0]); self.vars["status"].set("New"); self.vars["email_status"].set("Not checked"); self.notes.delete("1.0", "end")

    def delete(self):
        if self.selected and messagebox.askyesno("Confirm", "Delete selected lead?"):
            self.conn.execute("DELETE FROM leads WHERE id=?", (self.selected,)); self.conn.commit(); self.clear(); self.refresh()

    def audit_current(self):
        url = self.vars["website"].get().strip()
        def done(a, err):
            if err: messagebox.showerror("Audit failed", err); return
            self.vars["need_signal"].set(" | ".join(a["signals"]))
            if a["emails"] and not self.vars["email"].get(): self.vars["email"].set(a["emails"][0]); self.vars["email_status"].set("Format valid")
            messagebox.showinfo("Website audit", "\n".join("• " + s for s in a["signals"]) + ("\n\nPublic email: " + ", ".join(a["emails"]) if a["emails"] else "") + "\n\nPress SAVE to keep this.")
        self.bg(lambda: engine.audit(url), done)

    def pitch_current(self):
        d = self.formdata()
        if not d["business"]: messagebox.showinfo("Lead", "Enter or select a lead first."); return
        def done(res, err):
            if err: messagebox.showerror("Failed", err); return
            text, note = res; w = ctk.CTkToplevel(self); w.title("AI Pitch - review before sending"); w.geometry("640x520"); w.configure(fg_color=BG); w.after(100, w.lift)
            self.lab(w, note, 11, CYA, "bold").pack(anchor="w", padx=20, pady=(18, 6))
            t = ctk.CTkTextbox(w, fg_color=CARD, corner_radius=14, font=F(13), wrap="word"); t.pack(fill="both", expand=True, padx=20); t.insert("1.0", text)
            self.btn(w, "COPY MESSAGE", lambda: (self.clipboard_clear(), self.clipboard_append(t.get("1.0", "end"))), GRN, fg="#04251c").pack(pady=16)
        self.bg(lambda: engine.pitch(engine.load_cfg(), d), done)

    def verify_email(self):
        e = self.vars["email"].get().strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e): self.vars["email_status"].set("Invalid / no MX"); messagebox.showwarning("Email", "Not a valid email format."); return
        dom = e.rsplit("@", 1)[1].lower(); self.vars["email_status"].set("Format valid")
        try:
            o = subprocess.run(["nslookup", "-type=mx", dom], capture_output=True, text=True, timeout=8); t = (o.stdout or "") + (o.stderr or "")
            if re.search(r"mail exchanger|MX preference|MX record", t, re.I): self.vars["email_status"].set("MX record found")
            else: socket.gethostbyname(dom); self.vars["email_status"].set("Domain resolves")
            messagebox.showinfo("Email check", f"Result: {self.vars['email_status'].get()}\n\nThis does NOT prove the mailbox exists.")
        except Exception: self.vars["email_status"].set("Unknown"); messagebox.showwarning("Email", "Could not check. Verify your internet connection.")

    def open_site(self):
        u = self.vars["website"].get().strip()
        if u: webbrowser.open(u if u.startswith("http") else "https://" + u)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="shawon_leads.csv", filetypes=[("CSV", "*.csv")])
        if not path: return
        rows = self.conn.execute("SELECT * FROM leads ORDER BY score DESC").fetchall()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(KEYS + ["score"])
            for r in rows: w.writerow([r[k] for k in KEYS] + [r["score"]])
        messagebox.showinfo("Exported", f"Saved {len(rows)} leads.")

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")]); added = 0
        if not path: return
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    d = {k: (row.get(k) or "").strip() for k in KEYS}
                    if not d["business"] or self.conn.execute("SELECT id FROM leads WHERE lower(business)=lower(?) AND lower(website)=lower(?)", (d["business"], d["website"])).fetchone(): continue
                    d["status"] = d["status"] or "New"; d["email_status"] = d["email_status"] or "Not checked"; self.insert(d); added += 1
            self.conn.commit(); self.refresh(); messagebox.showinfo("Import", f"Imported {added} new leads.")
        except Exception as e: messagebox.showerror("Import error", str(e))

    # ---------- Settings ----------
    def build_settings(self):
        p = self.pages["set"]; self.head(p, "Settings", "Everything works free. Keys are optional and stay on your computer."); cfg = engine.load_cfg()
        c = self.card(p); c.pack(fill="x", padx=30); self.kv = {}
        self.lab(c, "AI MESSAGE WRITER", 12, TXT, "bold").grid(row=0, column=0, sticky="w", padx=22, pady=(18, 10))
        self.kv["provider"] = tk.StringVar(value=cfg.get("provider", engine.PROVIDERS[1]))
        self.lab(c, "Provider", 10, MUT, "bold").grid(row=1, column=0, sticky="w", padx=22); self.menu(c, self.kv["provider"], engine.PROVIDERS, 300).grid(row=1, column=1, sticky="w", padx=10, pady=4)
        for r, (k, t) in enumerate([("gemini_key", "Gemini key (free)"), ("groq_key", "Groq key (free)"), ("pitch_lang", "Message language")], 2):
            self.kv[k] = tk.StringVar(value=cfg.get(k, "")); self.lab(c, t, 10, MUT, "bold").grid(row=r, column=0, sticky="w", padx=22)
            e = self.ent(c, self.kv[k], "English" if k == "pitch_lang" else "paste key here", 420); e.grid(row=r, column=1, sticky="w", padx=10, pady=4)
            if k != "pitch_lang": e.configure(show="•")
        b = ctk.CTkFrame(c, fg_color="transparent"); b.grid(row=5, column=0, columnspan=3, sticky="w", padx=22, pady=16)
        self.btn(b, "SAVE SETTINGS", lambda: (engine.save_cfg({k: v.get().strip() for k, v in self.kv.items()}), messagebox.showinfo("Saved", "Settings saved.")), GRN, fg="#04251c", width=160).pack(side="left")
        self.btn(b, "Get free Gemini key", lambda: webbrowser.open("https://aistudio.google.com/apikey"), CARD2, width=170).pack(side="left", padx=10)
        self.btn(b, "Get free Groq key", lambda: webbrowser.open("https://console.groq.com/keys"), CARD2, width=160).pack(side="left")
        i = self.card(p); i.pack(fill="x", padx=30, pady=18)
        self.lab(i, "HOW THE FREE MODE WORKS", 12, TXT, "bold").pack(anchor="w", padx=22, pady=(16, 6))
        for t in ["OpenStreetMap is free but its business coverage is incomplete and varies by city/category.",
                  "Google and Bing open targeted browser searches; they do not automatically scrape or import results.",
                  "Website audit checks a few public pages using basic heuristics, not a full SEO/security audit.",
                  "Email discovery only finds addresses published on those pages; MX checks cannot prove an inbox exists.",
                  "Free AI services can change quotas, availability and terms. Review privacy terms before sending data.",
                  "Use public business contact details, personalize outreach, honor opt-outs and follow local anti-spam/privacy laws."]: self.lab(i, "•  " + t, 11, MUT).pack(anchor="w", padx=22, pady=2)
        self.lab(i, "", 4).pack()
        self.btn(p, "BACKUP DATABASE", lambda: (lambda t: t and (self.conn.commit(), shutil.copy2(DB, t), messagebox.showinfo("Backup", "Saved.")))(filedialog.asksaveasfilename(defaultextension=".db", initialfile="backup.db")), CARD2, width=180).pack(anchor="w", padx=30)


if __name__ == "__main__":
    App().mainloop()
