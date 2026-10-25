"""Small phone-friendly web UI for managing cards."""
import json
import os
import time
import urllib.parse
import urllib.request

from flask import Flask, jsonify, redirect, render_template_string, request

from .cards import CardMap, last_scan, normalize_uri
from .main import CARDS_FILE, LAST_SCAN_FILE

app = Flask(__name__)
cards = CardMap(CARDS_FILE)
RECENT_SECONDS = 120

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jukebox cards</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:560px;margin:1rem auto;padding:0 1rem;background:#fafafa}
 .box{background:#fff;border:1px solid #ddd;border-radius:10px;padding:1rem;margin-bottom:1rem}
 input{width:100%;padding:.7rem;margin:.3rem 0 .8rem;font-size:1rem;box-sizing:border-box}
 button{padding:.7rem 1.2rem;font-size:1rem;border:0;border-radius:8px;background:#1db954;color:#fff}
 button.del{background:#c33;padding:.4rem .8rem}
 .msg{padding:.7rem;border-radius:8px;background:#e8f5e9;margin-bottom:1rem}
 .err{background:#fdecea}
 .card{display:flex;justify-content:space-between;align-items:center;gap:.5rem;border-top:1px solid #eee;padding:.6rem 0}
 .small{color:#777;font-size:.8rem;word-break:break-all}
</style></head><body>
<h1>🎵 Jukebox cards</h1>
{% if msg %}<div class="msg {{ 'err' if err }}">{{ msg }}</div>{% endif %}

<div class="box">
 <h2>Add or change a card</h2>
 <p id="status">Tap a card on the jukebox...</p>
 <form method="post" action="/save">
  <input type="hidden" name="uid" id="uid" value="{{ uid }}">
  <label>Spotify link (Share &gt; Copy link)</label>
  <input name="link" id="link" placeholder="https://open.spotify.com/track/..." required>
  <label>Name</label>
  <input name="name" id="name" placeholder="e.g. Bedtime songs">
  <button id="save" disabled>Save card</button>
 </form>
</div>

<div class="box">
 <h2>Saved cards</h2>
 {% for uid, c in cards.items() %}
  <div class="card"><div><b>{{ c.name or '(no name)' }}</b>
   <div class="small">{{ c.uri }}<br>Card {{ uid }}</div></div>
   <form method="post" action="/delete" onsubmit="return confirm('Remove this card?')">
    <input type="hidden" name="uid" value="{{ uid }}"><button class="del">Remove</button></form>
   <button type="button" onclick="pick('{{ uid }}')">Change</button></div>
 {% else %}<p>No cards yet.</p>{% endfor %}
</div>

<script>
const uid=document.getElementById('uid'), st=document.getElementById('status'), save=document.getElementById('save');
function pick(u){uid.value=u;st.textContent='Editing card '+u;save.disabled=false;scrollTo(0,0)}
async function poll(){
 try{const r=await (await fetch('/api/last-scan')).json();
  if(r.uid && r.recent && !uid.dataset.manual){
   if(uid.value!==r.uid){uid.value=r.uid}
   st.textContent=r.known?'Card '+r.uid+' is already set up. Saving will replace it.':'New card detected: '+r.uid;
   save.disabled=false}
 }catch(e){}
}
document.querySelectorAll('.card button[type=button]').forEach(b=>b.addEventListener('click',()=>uid.dataset.manual=1));
if(uid.value){save.disabled=false;st.textContent='Card '+uid.value}
setInterval(poll,1500);poll();

document.getElementById('link').addEventListener('change',async e=>{
 const n=document.getElementById('name'); if(n.value)return;
 try{const r=await (await fetch('/api/title?url='+encodeURIComponent(e.target.value))).json();
  if(r.title)n.value=r.title}catch(_){}
});
</script></body></html>"""


def _render(msg: str = "", err: bool = False):
    cards.load()
    return render_template_string(PAGE, cards=cards.cards, msg=msg, err=err, uid="")


@app.get("/")
def index():
    return _render(request.args.get("msg", ""), request.args.get("err") == "1")


@app.get("/api/last-scan")
def api_last_scan():
    scan = last_scan(LAST_SCAN_FILE)
    if not scan:
        return jsonify(uid=None)
    cards.load()
    return jsonify(
        uid=scan["uid"],
        recent=time.time() - scan["time"] < RECENT_SECONDS,
        known=scan["uid"] in cards.cards,
    )


@app.get("/api/title")
def api_title():
    """Best-effort lookup of a name for the pasted link via Spotify oEmbed."""
    try:
        uri = normalize_uri(request.args.get("url", ""))
        _, kind, ident = uri.split(":")
        url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/{kind}/{ident}"
        with urllib.request.urlopen(url, timeout=5) as r:
            return jsonify(title=json.load(r).get("title", ""))
    except Exception:
        return jsonify(title="")


@app.post("/save")
def save():
    uid = request.form.get("uid", "").strip().upper()
    if not uid:
        return redirect("/?err=1&msg=" + urllib.parse.quote("Tap a card first."))
    try:
        uri = normalize_uri(request.form.get("link", ""))
    except ValueError:
        return redirect("/?err=1&msg=" + urllib.parse.quote("That doesn't look like a Spotify link."))
    cards.add(uid, uri, request.form.get("name", "").strip())
    return redirect("/?msg=" + urllib.parse.quote("Saved! Tap the card to try it."))


@app.post("/delete")
def delete():
    cards.remove(request.form.get("uid", ""))
    return redirect("/?msg=" + urllib.parse.quote("Card removed."))


def serve() -> None:
    app.run(host="0.0.0.0", port=int(os.environ.get("WEB_PORT", "80")))
