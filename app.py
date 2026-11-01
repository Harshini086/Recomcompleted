"""Recomai - personalised Indian government scheme recommender (Streamlit).
Run: pip install -r requirements.txt && streamlit run app.py
Scheme data is SAMPLE seed data (not official or current). Data is saved to ./data (demo storage, not secure)."""
import io, os, re, json, base64, hashlib, secrets, datetime as dt
from pathlib import Path
from urllib.parse import quote
import pandas as pd, streamlit as st
from PIL import Image, ImageOps

st.set_page_config(page_title="Recomai", page_icon="🌉", layout="wide")
ss, TODAY = st.session_state, dt.date.today()
ROOT = Path(__file__).parent / "data"; UPL = ROOT / "uploads"; UPL.mkdir(parents=True, exist_ok=True); DBF = ROOT / "db.json"
NEEDS = ["Education","Employment","Agriculture","Healthcare","Housing","Women & Child Welfare","Entrepreneurship","Pension","Skill Development","Financial Assistance"]
OCC = ["Student","Farmer","Entrepreneur","Employee","Job seeker","Senior citizen","Homemaker","Other"]
STATES = ["Tamil Nadu","Karnataka","Kerala","Maharashtra","Uttar Pradesh","Delhi","Gujarat","West Bengal","Other"]
DOCS = ["Aadhaar","Income Certificate","Residence Certificate","Mark Sheet","Community Certificate","Bank Passbook","Land Record"]
AST = ["Not Started","Documents Missing","Ready to Apply","Application Started","Completed"]
INC = {"Below ₹2.5 lakh":2.5,"₹2.5–5 lakh":5,"₹5–8 lakh":8,"Above ₹8 lakh":20}
PAGES = ["Home","Discover Schemes","How It Works","My Dashboard","Document Vault","Ask Setu","About","Admin"]
PROTECTED = {"My Dashboard","Document Vault","Onboarding","Profile"}
STEPS = ["Check the official guidelines","Prepare your documents","Apply through the official channel","Track your application"]
def sch(i,name,cat,desc,benefit,elig,a,inc,docs,dl="",states=(),occ=(),cats=(),g="",up="2026-09-01"):
    return dict(id=i,name=name,ministry=f"{cat} dept. (sample)",cat=cat,desc=desc,benefit=benefit,elig=elig,a=list(a),inc=inc,docs=list(docs),dl=dl,states=list(states),occ=list(occ),cats=list(cats),g=g,up=up,on=True)
SEED = [
 sch(1,"Sample Merit Scholarship","Education","Merit-based support for students from lower-income households.","Up to ₹20,000 per year","Students aged 16–30, income under ₹2.5 lakh",(16,30),2.5,["Aadhaar","Mark Sheet","Income Certificate","Bank Passbook"],"2026-12-31",occ=["Student"]),
 sch(2,"Sample Post-Matric Support","Education","Fee and maintenance support for SC/ST/OBC students.","Fee reimbursement + stipend","Students aged 16–35 from SC/ST/OBC, income under ₹2.5 lakh",(16,35),2.5,["Aadhaar","Community Certificate","Income Certificate","Mark Sheet"],"2026-11-30",occ=["Student"],cats=["SC","ST","OBC"],up="2026-08-15"),
 sch(3,"Sample Youth Skill Training","Skill Development","Short certified skill courses with placement support.","Free training + certificate","Ages 18–35, students and job seekers",(18,35),8,["Aadhaar","Residence Certificate","Bank Passbook"],"2027-03-31",occ=["Student","Job seeker"],up="2026-09-20"),
 sch(4,"Sample State Graduate Job Assistance","Employment","Monthly assistance for registered unemployed graduates.","Monthly allowance (amount to verify)","State residents aged 18–35, job seekers",(18,35),2.5,["Aadhaar","Residence Certificate","Mark Sheet","Income Certificate"],"2026-12-15",states=["Tamil Nadu"],occ=["Job seeker","Student"],up="2026-07-10"),
 sch(5,"Sample Farmer Income Support","Agriculture","Direct income support for landholding farmer families.","Periodic bank transfer","Farmers with land records, 18+",(18,100),20,["Aadhaar","Land Record","Bank Passbook"],occ=["Farmer"],up="2026-06-01"),
 sch(6,"Sample Women Entrepreneur Grant","Entrepreneurship","Seed grant and mentoring for women starting businesses.","Seed grant + mentoring","Women aged 18–50, income under ₹8 lakh",(18,50),8,["Aadhaar","Bank Passbook","Residence Certificate"],"2027-01-31",occ=["Entrepreneur","Homemaker","Job seeker","Employee"],g="Female",up="2026-08-01"),
 sch(7,"Sample Senior Citizen Pension","Pension","Monthly pension for older adults from low-income households.","Monthly pension","Age 60+, income under ₹3 lakh",(60,120),3,["Aadhaar","Income Certificate","Bank Passbook"],occ=["Senior citizen"],up="2026-05-20"),
 sch(8,"Sample Family Health Cover","Healthcare","Hospitalisation cover for eligible families.","Cashless cover up to a family limit","Families with income under ₹2.5 lakh",(0,120),2.5,["Aadhaar","Income Certificate","Residence Certificate"],up="2026-09-05"),
 sch(9,"Sample Rural Housing Assistance","Housing","Financial help to build or improve a basic home.","Construction assistance","Households under ₹3 lakh",(18,120),3,["Aadhaar","Income Certificate","Residence Certificate","Bank Passbook"],"2027-02-28",up="2026-04-18"),
 sch(10,"Sample Startup Credit Scheme","Entrepreneurship","Collateral-light loans for first-time entrepreneurs.","Loan support (terms to verify)","Ages 18–45, entrepreneurs and job seekers",(18,45),10,["Aadhaar","Bank Passbook","Residence Certificate"],"2027-03-31",occ=["Entrepreneur","Job seeker"],up="2026-08-25")]

# ---------- storage ----------
def load_db():
    try: db = json.loads(DBF.read_text("utf-8"))
    except Exception: db = {}
    db.setdefault("users",{}); db.setdefault("schemes",None); db.setdefault("stats",{"recs":0,"searches":{},"rec_ids":{}}); return db
def save_db():
    try: DBF.write_text(json.dumps(ss.db,ensure_ascii=False,indent=1),"utf-8")
    except Exception: st.toast("Couldn't save your data. Please try again.")
def bump(k,key):
    d=ss.db["stats"].setdefault(k,{}); d[key]=d.get(key,0)+1
def persist():
    if not ss.user or ss.demo: return
    e=ss.user["email"]; u=ss.db["users"][e]; u["profile"]=ss.profile; u["apps"]={str(k):v for k,v in ss.apps.items()}; docs={}
    for n,d in ss.docs.items():
        f=None
        if d.get("img"): f=str(UPL/f"{hashlib.md5(e.encode()).hexdigest()[:8]}_{n.replace(' ','_')}.jpg"); Path(f).write_bytes(d["img"])
        docs[n]=dict(s=d["s"],exp=str(d["exp"]) if d.get("exp") else None,up=str(d["up"]),file=f)
    u["docs"]=docs; save_db()
def load_user(e):
    u=ss.db["users"][e]; ss.user={"name":u["name"],"email":e}; ss.profile=u.get("profile"); ss.apps={int(k):v for k,v in u.get("apps",{}).items()}; ss.docs={}
    for n,d in u.get("docs",{}).items():
        img=None
        try: img=Path(d["file"]).read_bytes() if d.get("file") else None
        except Exception: pass
        ss.docs[n]=dict(s=d["s"],exp=dt.date.fromisoformat(d["exp"]) if d.get("exp") else None,up=dt.date.fromisoformat(d["up"]),img=img)
def pwhash(pw,salt): return hashlib.pbkdf2_hmac("sha256",pw.encode(),bytes.fromhex(salt),100000).hex()
if "db" not in ss:
    ss.db=load_db()
    for k,v in dict(page="Home",user=None,profile=None,docs={},apps={},demo=False,chat=[],cur=None,ob=0,P={},pending=None,ck=0).items(): ss[k]=v
    ss.schemes=ss.db["schemes"] or [dict(s) for s in SEED]

# ---------- style ----------
st.markdown("""<style>@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@400;500;700&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}h1,h2,h3{font-family:'DM Serif Display',Georgia,serif!important;font-weight:400!important}
.stApp{background:#F5F0E6}[data-testid=stSidebar]{background:#E9E1D3}.block-container{max-width:1150px;padding-top:2rem}
.stButton>button,.stLinkButton>a,.stFormSubmitButton>button{border-radius:999px;padding:.45rem 1.3rem;border:1px solid #171717;transition:all .2s}.stButton>button:hover{transform:translateY(-2px)}
.stButton>button[kind=primary],.stFormSubmitButton>button[kind=primary]{background:#5F6F52;border-color:#5F6F52;color:#fff}
[data-testid=stVerticalBlockBorderWrapper]{border-radius:24px;background:#fff;box-shadow:0 6px 24px rgba(0,0,0,.06)}
.hero{font-family:'DM Serif Display',serif;font-size:clamp(2.6rem,7vw,5rem);line-height:1.05;margin-bottom:.6rem}.mut{color:#66635C}.brand{font-family:'DM Serif Display',serif;font-size:1.9rem}
.pc{display:flex;flex-direction:column;align-items:center;justify-content:space-between;height:190px;padding:12px 8px 14px;background:#E9E1D3;border-radius:80px 20px 80px 20px;text-align:center;font-family:'DM Serif Display',serif;font-size:1rem;line-height:1.15;transition:transform .3s}
.pc.g{background:#5F6F52;color:#fff;border-radius:20px 80px 20px 80px}.pc:hover{transform:translateY(-6px)}.pc img{width:112px;height:112px}.pc div{min-height:2.3em;display:flex;align-items:center;justify-content:center}
.dk{background:#20231F;color:#F5F0E6;border-radius:36px;padding:2.5rem;margin:1rem 0}.dk h1{font-size:4rem;color:#F5F0E6;margin:.2rem 0}.dk p{color:#F5F0E6}
.pill{border-radius:999px;padding:2px 12px;font-size:.8rem;background:#f2e3c1}.pill.ok{background:#dfe8d6}.pill.bd{background:#f1d6cd}
.kv{display:flex;justify-content:space-between;padding:.55rem 0;border-bottom:1px solid #E9E1D3}.kv span:first-child{color:#66635C}
@media(prefers-reduced-motion:no-preference){.block-container{animation:f .5s}@keyframes f{from{opacity:0;transform:translateY(10px)}}}</style>""",unsafe_allow_html=True)

# ---------- helpers ----------
def hair(c): return f"<path d='M29 46c0-16 9-22 21-22s21 6 21 22c-6-8-12-11-21-11s-15 3-21 11z' fill='{c}'/>"
GL="<circle cx='42' cy='49' r='6' fill='none'/><circle cx='58' cy='49' r='6' fill='none'/><path d='M48 49h4'/>"
AV={"Student":("#f1c8a0","#e9b949","",hair("#2b1d12")+"<path d='M24 32l26-11 26 11-26 11z' fill='#171717'/><path d='M74 33v14' stroke='#e9b949' stroke-width='3'/>"),
 "Farmer":("#c98f5f","#c9743d","","<ellipse cx='50' cy='33' rx='33' ry='7' fill='#e8c872'/><path d='M34 33c0-14 8-20 16-20s16 6 16 20z' fill='#e8c872'/><path d='M34 30h32' stroke='#c0392b' stroke-width='4'/>"),
 "Entrepreneur":("#e8b98f","#2f3a4a","",hair("#171717")+"<path d='M42 70l8 8 8-8' fill='#fff'/><path d='M46 74l4 4 4-4-2 14h-4z' fill='#c0392b'/>"),
 "Working professional":("#8d5a3b","#8aa7c4","","<circle cx='36' cy='35' r='9' fill='#171717'/><circle cx='50' cy='29' r='10' fill='#171717'/><circle cx='64' cy='35' r='9' fill='#171717'/>"+GL+"<path d='M42 72l8 14 8-14' fill='none' stroke='#5F6F52' stroke-width='3'/>"),
 "Senior citizen":("#f0c8a8","#b86a77","",hair("#f5f5f5")+GL+"<path d='M41 55q9-4 18 0q-9 5-18 0z' fill='#f5f5f5'/>"),
 "Woman":("#e8b98f","#d9534f","<path d='M27 50c-3-26 9-33 23-33s26 7 23 33c0 14 2 22 7 32H20c5-10 7-18 7-32z' fill='#2b1d12'/>","<path d='M31 45c4-13 12-17 19-17s15 4 19 17c-8-4-14-8-19-8s-11 4-19 8z' fill='#2b1d12'/><circle cx='50' cy='38' r='2' fill='#c0392b' stroke='none'/>"),
 "Job seeker":("#d9a679","#6c8f7a","",hair("#4a2f1b")+"<circle cx='80' cy='64' r='9' fill='#fff' fill-opacity='.55'/><path d='M74 71l-9 11' stroke-width='4'/>")}
def avatar(n):
    k,sh,bk,fr=AV[n]
    svg=f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' stroke='#171717' stroke-width='2' stroke-linejoin='round' stroke-linecap='round'><circle cx='50' cy='52' r='46' fill='#fff' fill-opacity='.3' stroke='none'/>{bk}<rect x='44' y='60' width='12' height='14' fill='{k}'/><path d='M16 100c0-20 14-30 34-30s34 10 34 30z' fill='{sh}'/><circle cx='50' cy='48' r='21' fill='{k}'/><circle cx='29.5' cy='50' r='3.5' fill='{k}'/><circle cx='70.5' cy='50' r='3.5' fill='{k}'/>{fr}<circle cx='43' cy='49' r='2.4' fill='#171717' stroke='none'/><circle cx='57' cy='49' r='2.4' fill='#171717' stroke='none'/><circle cx='38' cy='57' r='3.5' fill='#ff9a8a' stroke='none' opacity='.6'/><circle cx='62' cy='57' r='3.5' fill='#ff9a8a' stroke='none' opacity='.6'/><path d='M43 58q7 6 14 0' fill='none'/></svg>"
    return "data:image/svg+xml;base64,"+base64.b64encode(svg.encode()).decode()
def go(p,cur=None,mode=None):
    ss.page=p
    if cur is not None: ss.cur=cur
    if mode: ss.am=mode
def ask(q): ss.pending=q; go("Ask Setu")
def logout(): ss.update(user=None,profile=None,docs={},apps={},demo=False,chat=[]); go("Home")
def dstat(n):
    d=ss.docs.get(n)
    if not d: return "Missing"
    return "Expiring Soon" if d.get("exp") and (d["exp"]-TODAY).days<60 else d["s"]
def pill(s): return f'<span class="pill {"ok" if s in("Verified","Uploaded") else "bd" if s=="Missing" else ""}">{s}</span>'
def score(s,p):
    if not p: return None
    miss=[d for d in s["docs"] if dstat(d)=="Missing"]
    chk=[(20,s["a"][0]<=p["age"]<=s["a"][1],"Age requirement satisfied","Age is outside the stated range"),
     (25,p["inc"]<=s["inc"],"Income requirement satisfied","Income may exceed the stated limit"),
     (15,not s["states"] or p["state"] in s["states"],"State requirement satisfied","Scheme is limited to other states"),
     (15,not s["occ"] or p["occ"] in s["occ"],"Occupation requirement satisfied","Scheme targets a different occupation"),
     (10,(not s["cats"] or p["cat"] in s["cats"]) and (not s["g"] or s["g"]==p["gender"]),"Category requirement satisfied","Category or gender criteria not met"),
     (10,s["cat"] in p["needs"],"Matches what you're looking for","Not in your selected needs")]
    f=[(ok,y if ok else n) for w,ok,y,n in chk]+[(not miss,"All documents available" if not miss else f"{len(miss)} document(s) missing")]
    return dict(total=round(sum(w for w,ok,*_ in chk if ok)+5*(len(s["docs"])-len(miss))/len(s["docs"])),f=f)
def ranked(): return sorted([(s,score(s,ss.profile)) for s in ss.schemes if s["on"]],key=lambda x:-(x[1]["total"] if x[1] else 0))
def card(s,m,k):
    with st.container(border=True):
        a,b=st.columns([3,1]); a.caption(s["cat"].upper())
        if m: b.markdown(f"**{m['total']}% Match**")
        st.markdown(f"### {s['name']}"); st.write(s["desc"])
        if m: st.progress(m["total"]/100)
        st.markdown(f"**Benefit:** {s['benefit']}  \n**Who:** {s['elig']}"); st.caption(f"{len(s['docs'])} documents · Updated {s['up']} · Sample data")
        st.button("View Details",key=f"v{k}{s['id']}",on_click=go,args=("Scheme Details",s["id"]))
def grid(items,k,n=3):
    cols=st.columns(n)
    for i,(s,m) in enumerate(items):
        with cols[i%n]: card(s,m,k)
def need_profile():
    st.info("Complete your profile to discover better matches."); st.button("Build my profile",on_click=go,args=("Onboarding",))
def demo():
    d=lambda n:TODAY+dt.timedelta(days=n)
    ss.update(demo=True,user={"name":"Aarav","email":"demo@recomai.demo"},apps={1:"Documents Missing",3:"Application Started"},
     profile=dict(name="Aarav",state="Tamil Nadu",district="Chennai",area="Urban",age=21,gender="Male",marital="Single",cat="OBC",disab="No",occ="Student",inc=2.5,emp="Student",fam=4,needs=["Education","Skill Development","Employment"]),
     docs={"Aadhaar":dict(s="Verified",exp=None,up=d(-60)),"Income Certificate":dict(s="Uploaded",exp=d(30),up=d(-300)),"Residence Certificate":dict(s="Uploaded",exp=None,up=d(-40)),"Mark Sheet":dict(s="Uploaded",exp=None,up=d(-20)),"Bank Passbook":dict(s="Uploaded",exp=None,up=d(-10))})
    go("My Dashboard")

# ---------- pages ----------
PERS={"Student":("Student",""),"Farmer":("Farmer",""),"Entrepreneur":("Entrepreneur",""),"Working professional":("Employee",""),"Senior citizen":("Senior citizen",""),"Woman":("All","women"),"Job seeker":("Job seeker","")}
FT={"Personalized Matching":"Discover Schemes","Eligibility Explained":"Ask Setu","Document Ready":"Document Vault"}
def persona_go(n):
    o,q=PERS[n]; ss.update(df_q=q,df_cat="All",df_state="All",df_occ=o); go("Discover Schemes")
def home():
    st.markdown('<div class="hero">Government schemes,<br>matched to you.</div><p class="mut" style="max-width:560px;font-size:1.15rem">Discover government benefits based on your profile, understand your eligibility, organize your documents and take the next step — all in one place.</p>',unsafe_allow_html=True)
    a,b,c,_=st.columns([1.3,1,1.2,2])
    a.button("Find My Schemes →",type="primary",on_click=go,args=("Discover Schemes" if ss.user else "Sign Up",)); b.button("Explore Schemes",on_click=go,args=("Discover Schemes",)); c.button("Try demo profile",on_click=demo)
    st.write("")
    for i,(col,n) in enumerate(zip(st.columns(7),AV)):
        col.markdown(f'<div class="pc {"g" if i%2 else ""}"><img src="{avatar(n)}" alt="{n}"><div>{n}</div></div>',unsafe_allow_html=True)
        col.button("Explore →",key="pe"+n,on_click=persona_go,args=(n,),use_container_width=True)
    st.caption("Personalized • Transparent • Citizen-first"); quick()
    st.header("One profile. Hundreds of possibilities.")
    for col,(t,d) in zip(st.columns(3),[("Personalized Matching","Find schemes that fit your profile, needs and circumstances."),("Eligibility Explained","Understand why a scheme matches you instead of receiving a mysterious recommendation."),("Document Ready","Know exactly which documents you already have and what is still required.")]):
        with col.container(border=True):
            st.subheader(t); st.write(d); st.button("Explore →",key="ft"+t,on_click=go,args=(FT[t],))
    how(); st.header("Your best matches" if ss.profile else "Popular schemes, simplified."); grid(ranked()[:3],"h"); st.button("Explore All Schemes →",on_click=go,args=("Discover Schemes",))
    st.markdown('<div class="dk"><p>Don\'t know where to start?</p><h1>Ask Setu.</h1><p>Your conversational guide to government schemes.</p><p><i>You:</i> I am a 21-year-old student. What schemes might I qualify for?<br><i>Setu AI:</i> Based on the information in your profile, I found several potential education and skill-development opportunities. Here are your strongest matches...</p></div>',unsafe_allow_html=True)
    st.button("Open Setu AI →",on_click=go,args=("Ask Setu",))
    st.header("Your documents. Always ready."); st.write("Keep important documents organized and connect them directly to scheme requirements.")
    for col,(n,s) in zip(st.columns(5),[("Aadhaar","Uploaded"),("Income Certificate","Expiring Soon"),("Residence Certificate","Uploaded"),("Mark Sheet","Uploaded"),("Community Certificate","Missing")]):
        with col.container(border=True):
            st.markdown(f"**{n}**<br>{pill(s)}",unsafe_allow_html=True); st.button("Scan →",key="dp"+n,on_click=scan_for,args=(n,))
    st.header("You may already qualify for more than you think."); st.button("Check My Eligibility →",type="primary",on_click=go,args=("Discover Schemes" if ss.user else "Sign Up",))
def how():
    st.header("From discovery to application.")
    for col,(i,t) in zip(st.columns(4),enumerate(["Tell us about you","Discover your matches","Prepare your documents","Take the next step"],1)): col.markdown(f"<span class='brand' style='color:#5F6F52'>0{i}</span>",unsafe_allow_html=True); col.subheader(t)
def discover():
    st.title("Discover schemes"); q=st.text_input("Search",placeholder="Search schemes...",label_visibility="collapsed",key="df_q")
    with st.expander("Filters",expanded=True):
        c=st.columns(4); cat=c[0].selectbox("Category",["All"]+NEEDS,key="df_cat"); stt=c[1].selectbox("State",["All"]+STATES,key="df_state"); oc=c[2].selectbox("Occupation",["All"]+OCC,key="df_occ"); age=c[3].number_input("Age (0 = any)",0,120,0)
        c=st.columns(3); inc=c[0].number_input("Income ₹ lakh (0 = any)",0.0,50.0,0.0); stat=c[1].selectbox("Status",["Any","Open","Closed"]); so=c[2].selectbox("Sort",["Best match","Recently updated","Category"])
    if cat!="All" and ss.get("_lc")!=cat: ss._lc=cat; bump("searches",cat); save_db()
    R=[(s,m) for s,m in ranked() if (not q or q.lower() in (s["name"]+s["desc"]).lower()) and cat in("All",s["cat"]) and (stt=="All" or not s["states"] or stt in s["states"]) and (oc=="All" or not s["occ"] or oc in s["occ"]) and (not age or s["a"][0]<=age<=s["a"][1]) and (not inc or s["inc"]>=inc) and stat!="Closed"]
    if so=="Recently updated": R.sort(key=lambda x:x[0]["up"],reverse=True)
    if so=="Category": R.sort(key=lambda x:x[0]["cat"])
    if not ss.profile: need_profile()
    if R: grid(R,"d")
    else: st.warning("We couldn't find a close match. Try adjusting your filters.")
def track(sid):
    s=next(x for x in ss.schemes if x["id"]==sid)
    ss.apps[sid]="Ready to Apply" if all(dstat(d)!="Missing" for d in s["docs"]) else "Documents Missing"; persist(); st.toast("Added to your applications"); go("My Dashboard")
def details():
    s=next((x for x in ss.schemes if x["id"]==ss.cur),None)
    if not s: st.error("Unable to load this scheme."); return st.button("Back to schemes",on_click=go,args=("Discover Schemes",))
    m=score(s,ss.profile); st.button("← All schemes",on_click=go,args=("Discover Schemes",))
    st.caption(s["cat"].upper()); st.title(s["name"]); st.caption(f"{s['ministry']} · Deadline: {s['dl'] or 'None listed'} · Sample data")
    if m: st.header(f"{m['total']}% Match"); st.progress(m["total"]/100); st.caption("Recommended — a potential match, not an official decision.")
    a,b=st.columns(2)
    with a.container(border=True): st.subheader("Overview"); st.write(s["desc"]); st.write(f"**Benefits:** {s['benefit']}"); st.write(f"**Eligibility:** {s['elig']}")
    with b.container(border=True):
        st.subheader("Why you match")
        for ok,t in (m["f"] if m else []): st.write(("✓ " if ok else "⚠ ")+t)
        if not m: st.write("Build your profile to see why."); st.button("Build profile",on_click=go,args=("Onboarding",))
    have=[d for d in s["docs"] if dstat(d)!="Missing"]; miss=[d for d in s["docs"] if d not in have]; a,b=st.columns(2)
    with a.container(border=True):
        st.subheader("Required documents"); st.write("**Available:** "+(", ".join(have) or "None yet")); st.write("**Missing:** "+(", ".join(miss) or "None")); st.button("Open vault",on_click=go,args=("Document Vault",))
    with b.container(border=True):
        st.subheader("Application process")
        for i,t in enumerate(STEPS,1): st.write(f"**Step {i}** {t}")
    st.info("Recomai is an informational and recommendation platform and is not a government authority. Always verify eligibility using the official scheme guidelines before applying.")
    c=st.columns(3); c[0].link_button("Continue to Official Website →","https://www.google.com/search?q="+quote(s["name"].replace("Sample ","")+" official government scheme"))
    c[1].button("Track this application",on_click=track if ss.user else go,args=(s["id"],) if ss.user else ("Sign In",)); c[2].button("Ask Setu about this scheme",on_click=ask,args=("Explain this scheme simply",))
    st.caption("No verified official URL is connected for sample data; the button runs a web search for the official page.")
def setapp(sid): ss.apps[sid]=ss[f"a{sid}"]; persist()
def rmapp(sid): ss.apps.pop(sid,None); persist()
def dashboard():
    p=ss.profile; h=dt.datetime.now().hour; st.title(f"Good {'morning' if h<12 else 'afternoon' if h<17 else 'evening'}, {ss.user['name']}."); st.write("Here's what's waiting for you."+(f" Personalised for a {p['age']}-year-old {p['occ'].lower()} in {p['state']}." if p else ""))
    pc=min(100,60+(10 if p and p["needs"] else 0)+5*len(ss.docs)) if p else 20
    a,b=st.columns([4,1]); a.progress(pc/100,text=f"Profile completion {pc}%"); b.button("Complete Profile",on_click=start_ob)
    top=next(((s,m) for s,m in ranked() if m and m["total"]>=50),None)
    if top:
        s,m=top; miss=[d for d in s["docs"] if dstat(d)=="Missing"]
        with st.container(border=True):
            st.subheader("Your next best step"); st.write(f"**{s['name']}** is your strongest match ({m['total']}%)."+(f" You still need: {', '.join(miss)}." if miss else " Your documents are ready, so you can start your application."))
            c=st.columns(4)
            for j,d in enumerate(miss[:3]): c[j].button(f"📷 Scan {d}",key=f"sc{d}",on_click=scan_for,args=(d,))
            if not miss: c[0].button("Track application",key="tk",on_click=track,args=(s["id"],))
    st.header("Your strongest matches"); R=[x for x in ranked() if x[1]][:4]
    if R: grid(R,"m",2)
    else: need_profile()
    st.header("Your Applications")
    rows=[(sid,stt,next((x for x in ss.schemes if x["id"]==sid),None)) for sid,stt in ss.apps.items()]; rows=[r for r in rows if r[2]]
    if not rows: st.info("You haven't started an application yet.")
    else:
        for c,t in zip(st.columns([3,2,2,1]),["Scheme","Status","Documents","Action"]): c.caption(t)
    for sid,stt,s in rows:
        c=st.columns([3,2,2,1]); c[0].write(s["name"]); c[1].selectbox("Status",AST,AST.index(stt),key=f"a{sid}",label_visibility="collapsed",on_change=setapp,args=(sid,))
        c[2].write(f"{sum(dstat(d)=='Missing' for d in s['docs'])} missing"); c[3].button("Remove",key=f"r{sid}",on_click=rmapp,args=(sid,))
    a,b=st.columns(2)
    with a.container(border=True): st.subheader("Document Vault"); st.write(f"{len(ss.docs)} documents stored"); st.caption(f"{sum(dstat(d) in ('Expiring Soon','Missing') for d in ss.docs)} documents need attention"); st.button("Open vault",on_click=go,args=("Document Vault",))
    with b.container(border=True):
        st.subheader("Ask Setu")
        for q in ["What can I apply for?","Why do I qualify?","What documents am I missing?","Show my best matches"]: st.button(q,key="q"+q,on_click=ask,args=(q,))
def prep(raw,enh,rot):
    im=Image.open(io.BytesIO(raw)).convert("RGB")
    if rot: im=im.rotate(-rot,expand=True)
    im.thumbnail((1200,1200))
    if enh: im=ImageOps.autocontrast(ImageOps.grayscale(im),cutoff=2).convert("RGB")
    b=io.BytesIO(); im.save(b,"JPEG",quality=70); return b.getvalue()
def scan_for(d): ss.vdoc=d; go("Document Vault")
def scanner(key):
    k=f"{key}{ss.ck}"
    if "vdoc" in ss: ss[k+"t"]=ss.pop("vdoc")
    n=st.selectbox("Which document is this?",DOCS,key=k+"t",format_func=lambda d:d+(" (missing)" if dstat(d)=="Missing" else ""))
    t1,t2=st.tabs(["📷 Scan with camera","⬆ Upload file"])
    with t1: cam=st.camera_input("Hold the document flat in good light, then capture",key=k+"c")
    with t2: up=st.file_uploader("Image or PDF",type=["png","jpg","jpeg","pdf"],key=k+"u")
    f=cam or up; c=st.columns(3)
    enh=c[0].checkbox("Enhance like a scan",True,key=k+"e"); rot=c[1].selectbox("Rotate (°)",[0,90,180,270],key=k+"r"); exp=c[2].date_input("Expiry date (optional)",value=None,key=k+"d")
    img=None
    if f is not None and (f.type or "").startswith("image/"):
        try: img=prep(f.getvalue(),enh,rot); st.image(img,caption="Preview of what will be saved",use_container_width=True)
        except Exception: st.error("We couldn't read that image. Please retake it."); f=None
    elif f is not None: st.info(f"PDF selected: {f.name}")
    if st.button("Save to my vault",type="primary",key=k+"s"):
        if f is None: st.error("Capture or choose a document first.")
        else: ss.docs[n]=dict(s="Uploaded",exp=exp,up=TODAY,img=img,scan=True); persist(); ss.ck+=1; st.toast(f"{n} saved to your vault"); st.rerun()
NEEDKW={"scholar":"Education","education":"Education","study":"Education","skill":"Skill Development","job":"Employment","employment":"Employment","farm":"Agriculture","health":"Healthcare","house":"Housing","home loan":"Housing","pension":"Pension","loan":"Entrepreneurship","business":"Entrepreneurship"}
def parse_me(q):
    t=q.lower(); out={}
    m=re.search(r"(\d{1,3})[- ]?(?:year|yr)s?[- ]?old|\baged?\s*(?:is\s*)?(\d{1,3})|\bi(?:'m| am)\s+(\d{1,3})\b",t)
    if m: out["age"]=int(next(g for g in m.groups() if g))
    for x in STATES:
        if x.lower() in t: out["state"]=x
    for o,kw in {"Student":["student"],"Farmer":["farmer"],"Entrepreneur":["entrepreneur"],"Job seeker":["job seeker","unemployed"],"Senior citizen":["senior citizen","retired"],"Homemaker":["homemaker"],"Employee":["employee","working professional"]}.items():
        if any(k in t for k in kw): out["occ"]=o
    m=re.search(r"(?:below|under|less than|up ?to|income of|earn)\D{0,12}(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|l)\b",t)
    if m: v=float(m.group(1)); out["inc"]=2.5 if v<=2.5 else 5 if v<=5 else 8 if v<=8 else 20
    if re.search(r"\b(woman|female|girl)\b",t): out["gender"]="Female"
    elif re.search(r"\b(man|male|boy)\b",t): out["gender"]="Male"
    return out
def quick():
    st.header("Find your schemes in 30 seconds")
    with st.form("qm"):
        c=st.columns(5); age=c[0].number_input("Your age",0,120,21); g=c[1].selectbox("Gender",["Male","Female","Other"]); stt=c[2].selectbox("State",STATES); occ=c[3].selectbox("Occupation",OCC); inc=c[4].selectbox("Household income",list(INC))
        needs=st.multiselect("What are you looking for?",NEEDS)
        go_=st.form_submit_button("Show my matches",type="primary")
    if go_:
        base=dict(name=(ss.user or {}).get("name","Guest"),district="",area="Urban",marital="Single",cat="General",disab="No",emp="",fam=4); base.update(ss.profile or {})
        ss.profile=dict(base,age=int(age),gender=g,state=stt,occ=occ,inc=INC[inc],needs=needs)
        if ss.user: persist()
        st.success("Here are your personalised matches."+("" if ss.user else " Create a free account to save your profile and track applications."))
        grid(ranked()[:3],"qm")
def deldoc(n): ss.docs.pop(n,None); persist()
def vault():
    st.title("Document vault"); st.caption("Demo storage: files are saved on the app server's disk without encryption. Not government-grade security.")
    miss=[d for d in DOCS if dstat(d)=="Missing"]
    if miss:
        st.write("**Scan next:**")
        for c,d in zip(st.columns(min(len(miss),4)),miss[:4]): c.button(f"📷 {d}",key="sn"+d,on_click=lambda d=d:ss.update(vdoc=d),use_container_width=True)
    cols=st.columns(3)
    for i,n in enumerate(DOCS):
        d=ss.docs.get(n)
        with cols[i%3].container(border=True):
            st.markdown(f"**{n}** {pill(dstat(n))}",unsafe_allow_html=True)
            st.caption(f"Uploaded {d['up']} · Expiry {d['exp'] or 'none'}" if d else "Not uploaded")
            if d and d.get("img"): st.image(d["img"],use_container_width=True)
            if d: st.button("Delete",key=f"x{n}",on_click=deldoc,args=(n,))
    st.header("Scan or upload a document"); scanner("v")
BAD="I don't have enough verified information to confirm that. Please check the official scheme guidelines."
def reply0(q):
    q=q.lower(); p=ss.profile; R=[x for x in ranked() if x[1]]; cur=next((s for s in ss.schemes if s["id"]==ss.cur),None) if ss.page=="Ask Setu" and ss.get("_from_scheme") else None
    if any(w in q for w in("simply","explain")) and ss.cur: 
        s=next((x for x in ss.schemes if x["id"]==ss.cur),None)
        return (f"{s['name']}: {s['desc']} Benefit: {s['benefit']}. Who it's for: {s['elig']}. This is sample data; check the official guidelines.",[]) if s else (BAD,[])
    if not p and any(w in q for w in("find","apply","match","qualif","eligible","why","next","best")): return "Complete your profile first so I can match schemes to you, or try the demo profile.",[]
    if any(w in q for w in("why","eligible","qualify")) and R:
        s,m=R[0]; return f"For {s['name']} ({m['total']}% match):\n\n"+"\n\n".join(("✓ " if ok else "⚠ ")+t for ok,t in m["f"])+"\n\nThis is a recommendation, not an official decision.",[]
    if any(w in q for w in("document","missing","need")) and R:
        s=R[0][0]; miss=[d for d in s["docs"] if dstat(d)=="Missing"]; return f"For {s['name']} you need: {', '.join(s['docs'])}.\n\n"+("Still missing: "+", ".join(miss) if miss else "You have all of them in your vault."),[]
    if any(w in q for w in("find","apply","match","qualif","best","next","what can")):
        ids=[s["id"] for s,m in R if m["total"]>=50][:3]
        for i in ids: bump("rec_ids",str(i))
        ss.db["stats"]["recs"]+=1; save_db(); return ("Based on your profile, here are the strongest potential matches:" if ids else BAD),ids
    return BAD,[]
def reply(q):
    upd=parse_me(q); note=""
    if upd:
        base=ss.profile or dict(name=(ss.user or {}).get("name","Guest"),state="Tamil Nadu",district="",area="Urban",age=21,gender="Male",marital="Single",cat="General",disab="No",occ="Other",inc=20,emp="",fam=4,needs=[])
        upd["needs"]=list(base.get("needs",[]))+[v for k,v in NEEDKW.items() if k in q.lower() and v not in base.get("needs",[])]
        ss.profile=dict(base,**upd)
        if ss.user: persist()
        note="I've updated your profile with: "+", ".join(f"{k} = {v}" for k,v in upd.items() if k!="needs")+".\n\n"
        if not any(w in q.lower() for w in("why","document","missing","explain")): q+=" find my matches"
    t,ids=reply0(q); return note+t,ids
def chat():
    st.title("Ask Setu"); st.caption("Setu AI is rule-based and answers only from your profile and the sample scheme data.")
    if not ss.chat: ss.chat.append(("assistant","Hi, I'm Setu AI. Ask me about schemes, eligibility, documents or next steps.",[]))
    q=ss.pending; ss.pending=None
    for c,l in zip(st.columns(5),["Find schemes for me","Why am I eligible?","What documents do I need?","Explain this scheme simply","What should I apply for next?"]): c.button(l,key="cp"+l,on_click=ask,args=(l,))
    q=st.chat_input("Tell me about yourself, e.g. I'm a 21-year-old student from Tamil Nadu, income below 2 lakh") or q
    if q: ss.chat.append(("user",q,[])); t,ids=reply(q); ss.chat.append(("assistant",t,ids))
    for i,(r,t,ids) in enumerate(ss.chat):
        with st.chat_message(r):
            st.write(t)
            for sid in ids:
                s=next(x for x in ss.schemes if x["id"]==sid); st.button(f"{s['name']} · {score(s,ss.profile)['total']}% match",key=f"c{i}{sid}",on_click=go,args=("Scheme Details",sid))
def finish_login(e):
    g=ss.profile; load_user(e); ss.demo=False
    if g and not ss.profile: ss.profile=g; persist()
    t=ss.pop("after",None) or ("My Dashboard" if ss.profile else "Onboarding")
    if t=="My Dashboard" and not ss.profile: t="Onboarding"
    if t=="Onboarding": start_ob()
    else: go(t)
    st.rerun()
def auth():
    _,mid,_=st.columns([1,1.6,1])
    with mid:
        st.title("Welcome to Recomai")
        if "am" in ss: ss.authmode=ss.pop("am")
        ss.setdefault("authmode","Sign in"); mode=st.radio("Mode",["Sign in","Create account","Reset password"],key="authmode",horizontal=True,label_visibility="collapsed")
        with st.form("f_"+mode,clear_on_submit=False):
            name=st.text_input("Full name") if mode=="Create account" else ""
            email=st.text_input("Email",autocomplete="email").strip().lower(); pw=st.text_input("New password" if mode=="Reset password" else "Password",type="password")
            pw2=st.text_input("Confirm password",type="password") if mode!="Sign in" else pw
            ok=st.form_submit_button(mode,type="primary",use_container_width=True)
        if ok:
            U=ss.db["users"]
            if "@" not in email or "." not in email.split("@")[-1]: st.error("Enter a valid email address.")
            elif mode=="Create account" and not name.strip(): st.error("Please enter your name.")
            elif len(pw)<6: st.error("Password must be at least 6 characters.")
            elif pw!=pw2: st.error("Passwords don't match.")
            elif mode=="Create account":
                if email in U: st.error("An account with this email already exists. Try signing in.")
                else: salt=secrets.token_hex(8); U[email]=dict(name=name.strip(),salt=salt,hash=pwhash(pw,salt),profile=None,docs={},apps={}); save_db(); finish_login(email)
            elif mode=="Reset password":
                if email not in U: st.error("We couldn't find an account with that email.")
                else: salt=secrets.token_hex(8); U[email].update(salt=salt,hash=pwhash(pw,salt)); save_db(); st.success("Password updated. You can sign in now."); 
            else:
                u=U.get(email)
                if not u or not secrets.compare_digest(u["hash"],pwhash(pw,u["salt"])): st.error("Email or password is incorrect.")
                else: finish_login(email)
        st.caption("Demo storage: accounts are saved on this app's server. Password reset here does not send email.")
        st.button("Use demo account",on_click=demo,use_container_width=True)
def start_ob():
    for k in [k for k in ss if str(k).startswith("ob_")]: del ss[k]
    ss.ob=0; ss.P=dict(ss.profile or {}); P=ss.P
    if "inc" in P: P["incl"]=next((l for l,v in INC.items() if v==P["inc"]),"Below ₹2.5 lakh")
    P["dsel"]=list(ss.docs); go("Onboarding")
FIELDS={0:[("state","sel","State",STATES,"Tamil Nadu"),("district","txt","District",None,""),("area","rad","Area",["Urban","Rural"],"Urban")],
 1:[("age","num","Age",None,21),("gender","sel","Gender",["Male","Female","Other"],"Male"),("marital","sel","Marital status",["Single","Married","Widowed"],"Single"),("cat","sel","Category",["General","OBC","SC","ST"],"General"),("disab","rad","Disability",["No","Yes"],"No")],
 2:[("occ","rad","Occupation",OCC,"Student")],3:[("incl","sel","Annual household income",list(INC),"Below ₹2.5 lakh"),("emp","sel","Employment status",["Student","Employed","Self-employed","Unemployed","Retired"],"Student"),("fam","num","Family size",None,4)],
 4:[("needs","multi","What are you looking for?",NEEDS,[])],5:[("dsel","multi","Documents you already have",DOCS,[])]}
def obstep(d):
    for k,*_ in FIELDS[ss.ob]: ss.P[k]=ss["ob_"+k]
    ss.ob+=d
    if ss.ob==6:
        P=ss.P; P["inc"]=INC[P["incl"]]; P["name"]=ss.user["name"]; ss.profile={k:v for k,v in P.items() if k not in("incl","dsel")}
        for n in P["dsel"]: ss.docs.setdefault(n,dict(s="Uploaded",exp=None,up=TODAY))
        for n in [x for x in ss.docs if x not in P["dsel"] and not ss.docs[x].get("img") and not ss.docs[x].get("scan")]: ss.docs.pop(n)
        persist()
def onboard():
    i=ss.ob
    if i==6:
        st.title("Your profile is ready."); st.write(f"We matched {sum(1 for _,m in ranked() if m and m['total']>=50)} schemes to you."); return st.button("Find My Schemes →",type="primary",on_click=go,args=("Discover Schemes",))
    st.progress((i+1)/6,text=f"Step {i+1} of 6"); st.title(["Where do you live?","Tell us about yourself.","What do you do?","Your financial situation.","What are you looking for?","Your documents"][i])
    for k,kind,lab,opts,dflt in FIELDS[i]:
        key="ob_"+k
        if key not in ss: ss[key]=ss.P.get(k,dflt)
        _w={"sel":lambda:st.selectbox(lab,opts,key=key),"txt":lambda:st.text_input(lab,key=key),"rad":lambda:st.radio(lab,opts,key=key,horizontal=True),"num":lambda:st.number_input(lab,0,120,key=key),"multi":lambda:st.multiselect(lab,opts,key=key)}[kind]()
    if i==5:
        with st.expander("📷 Scan a document now (optional)"): scanner("ob")
    a,b,_=st.columns([1,1,4])
    if i: a.button("Back",on_click=obstep,args=(-1,))
    b.button("Finish" if i==5 else "Continue",type="primary",on_click=obstep,args=(1,))
def profile():
    p=ss.profile; st.title(ss.user["name"]); st.caption(ss.user["email"]+(" · demo account" if ss.demo else ""))
    if not p: need_profile()
    else:
        L=[("State",p["state"]),("District",p.get("district") or "—"),("Area",p["area"]),("Age",p["age"]),("Gender",p["gender"]),("Marital status",p["marital"]),("Category",p["cat"]),("Disability",p["disab"]),("Occupation",p["occ"]),("Income (up to ₹ lakh)",p["inc"]),("Employment",p["emp"]),("Family size",p["fam"]),("Looking for",", ".join(p["needs"]) or "—")]
        a,b=st.columns(2)
        for col,part in ((a,L[:7]),(b,L[7:])):
            with col.container(border=True):
                for k,v in part: st.markdown(f'<div class="kv"><span>{k}</span><span><b>{v}</b></span></div>',unsafe_allow_html=True)
        c=st.columns(3); c[0].metric("Documents stored",len(ss.docs)); c[1].metric("Applications",len(ss.apps)); c[2].metric("Strong matches",sum(1 for _,m in ranked() if m and m["total"]>=70))
    a,b,_=st.columns([1,1,4]); a.button("Edit profile",type="primary",on_click=start_ob); b.button("Sign out",on_click=logout)
def save_sch(): ss.db["schemes"]=ss.schemes; save_db()
def admin():
    st.title("Admin"); st.caption("Demo admin: there is no role check in this mini-project."); A=ss.schemes; S=ss.db["stats"]
    for col,(k,v) in zip(st.columns(6),[("Total schemes",len(A)),("Active",sum(s["on"] for s in A)),("Registered users",len(ss.db["users"])),("Recommendations",S["recs"]),("Applications (you)",len(ss.apps)),("Documents (you)",len(ss.docs))]): col.metric(k,v)
    a,b,c=st.columns(3); a.subheader("Most searched categories")
    if S["searches"]: a.bar_chart(pd.Series(S["searches"]))
    else: a.caption("No searches yet.")
    nm={str(s["id"]):s["name"].replace("Sample ","") for s in A}; b.subheader("Most recommended")
    if S.get("rec_ids"): b.bar_chart(pd.Series({nm.get(k,k):v for k,v in S["rec_ids"].items()}))
    else: b.caption("No recommendations yet.")
    mx=pd.Series([d for s in A for d in s["docs"] if dstat(d)=="Missing"]).value_counts(); c.subheader("Common missing documents")
    if len(mx): c.bar_chart(mx)
    else: c.caption("No data yet.")
    st.subheader("Manage schemes"); df=pd.DataFrame([dict(id=s["id"],name=s["name"],category=s["cat"],deadline=s["dl"],active=s["on"]) for s in A])
    ed=st.data_editor(df,hide_index=True,disabled=["id","category"],use_container_width=True,key="ed")
    c=st.columns([1,2,1])
    if c[0].button("Save changes",type="primary"):
        for _,r in ed.iterrows():
            s=next(x for x in A if x["id"]==r["id"]); s.update(name=r["name"],dl=r["deadline"] or "",on=bool(r["active"]))
        save_sch(); st.toast("Changes saved"); st.rerun()
    d=c[1].selectbox("Scheme to delete",[s["name"] for s in A],label_visibility="collapsed")
    if c[2].button("Delete scheme"): ss.schemes=[s for s in A if s["name"]!=d]; save_sch(); st.rerun()
    with st.form("edit"):
        st.write("**Update eligibility & documents**"); sn=st.selectbox("Scheme",[s["name"] for s in A]); x=st.columns(3); lo=x[0].number_input("Min age",0,120,18); hi=x[1].number_input("Max age",0,120,60); lim=x[2].number_input("Income limit (₹ lakh)",0.0,50.0,5.0); dd=st.multiselect("Required documents",DOCS,["Aadhaar"])
        if st.form_submit_button("Update scheme") and dd: s=next(y for y in A if y["name"]==sn); s.update(a=[lo,hi],inc=lim,docs=dd,up=str(TODAY)); save_sch(); st.success("Scheme updated.")
    with st.form("add"):
        st.write("**Add scheme**"); n=st.text_input("Name"); cat=st.selectbox("Category",NEEDS); ben=st.text_input("Benefit")
        if st.form_submit_button("Add scheme") and n.strip(): ss.schemes.append(sch(max(s["id"] for s in A)+1,n.strip(),cat,"Added via admin.",ben or "To be updated","To be updated",(0,120),20,["Aadhaar"],up=str(TODAY))); save_sch(); st.rerun()
def about():
    st.title("About Recomai"); st.write("Recomai — the bridge between you and the schemes you deserve — is a college engineering mini-project: a personalised government-scheme recommender.")
    st.info("Recomai is an informational platform, not a government authority. All schemes shown are SAMPLE seed data, not live or official. Recommendations are based on the information provided; always verify with the official guidelines.")

# ---------- shell ----------
if ss.page in PROTECTED and not ss.user: ss.after=ss.page; ss.page="Sign In"; ss.am="Sign in"
with st.sidebar:
    st.markdown('<div class="brand">Recomai</div><p class="mut">The bridge between you and the schemes you deserve.</p>',unsafe_allow_html=True)
    for p in PAGES: st.button(p,key="n"+p,use_container_width=True,type="primary" if ss.page==p else "secondary",on_click=go,args=(p,))
    st.divider()
    if ss.user: st.button(f"👤 {ss.user['name']}",use_container_width=True,on_click=go,args=("Profile",)); st.button("Sign Out",use_container_width=True,on_click=logout)
    else: st.button("Sign In",use_container_width=True,on_click=go,args=("Sign In",None,"Sign in")); st.button("Get Started",type="primary",use_container_width=True,on_click=go,args=("Sign Up",None,"Create account"))
def how_page():
    st.title("How Recomai works"); how()
PG={"Home":home,"Discover Schemes":discover,"Scheme Details":details,"How It Works":how_page,"My Dashboard":dashboard,"Document Vault":vault,"Ask Setu":chat,"About":about,"Admin":admin,"Sign In":auth,"Sign Up":auth,"Onboarding":onboard,"Profile":profile}
try: PG.get(ss.page,home)()
except Exception:
    st.error("Something went wrong. Please try again."); st.button("Go home",on_click=go,args=("Home",))
