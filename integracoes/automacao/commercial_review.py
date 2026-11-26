"""Commercial review: fail closed; never publishes or changes catalog."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = {"demand":25,"price":25,"commission":20,"seller":15,"conversion":15}

def evaluate(p, approved, evidence, now):
    reasons=[]
    price=p.get("price")
    if isinstance(price,bool) or not isinstance(price,(int,float)) or not math.isfinite(price) or price<=0:
        reasons.append("invalid price")
    if p.get("available") is not True:
        reasons.append("availability not confirmed")
    link=p.get("affiliateUrl")
    if not isinstance(link,str) or not re.fullmatch(r"https://(?:meli\.la/[A-Za-z0-9]+|(?:www\.)?mercadolivre\.com(?:\.br)?/sec/[A-Za-z0-9]+)",link) or approved.get(p.get("id"))!=link:
        reasons.append("unapproved affiliate link")
    if not str(p.get("imageUrl","")).startswith("https://"):
        reasons.append("image URL missing")
    score=0
    for key, weight in WEIGHTS.items():
        item=evidence.get(key,{})
        if not isinstance(item,dict): continue
        value=item.get("points")
        if type(value) is int and 0<=value<=weight and item.get("source") and item.get("date"):
            score+=value
    for key in ("price_verified","image_verified","availability_verified","identity_verified"):
        item=evidence.get(key,{})
        try:
            date=datetime.fromisoformat(item["date"].replace("Z","+00:00"))
            valid=item.get("confirmed") is True and bool(item.get("source")) and 0<=(now-date).total_seconds()<=86400
        except (KeyError,TypeError,ValueError,AttributeError):
            valid=False
        if not valid: reasons.append(key+" missing or stale")
    decision="review" if reasons else ("publish_candidate" if score>=80 else "review" if score>=60 else "reject")
    return {"id":p.get("id"),"name":p.get("name"),"score":score,"decision":decision,"reasons":reasons}

def main():
    catalog=json.loads((ROOT/"dados/catalogo.json").read_text())
    approved={p["id"]:p.get("affiliateUrl") for p in json.loads((ROOT/"links-afiliados.json").read_text())}
    path=ROOT/"dados/commercial-evidence.json"
    evidence=json.loads(path.read_text()) if path.exists() else {}
    now=datetime.now(timezone.utc)
    rows=[evaluate(p,approved,evidence.get(p["id"],{}),now) for p in catalog["products"]]
    print(json.dumps({"generated_at":now.isoformat(),"products":rows},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
