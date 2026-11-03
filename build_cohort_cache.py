import json,datetime as dt,time,pickle
import pandas as pd
from brand_matcher import BrandMatcher
DENY={"ipfs.io","sites.google.com","urlz.fr","tinyurl.com","is.gd","cutt.ly","bit.ly","t.co","goo.gl","rebrand.ly","s3.amazonaws.com","storage.googleapis.com","weebly.com","wixsite.com","github.io","netlify.app","vercel.app","herokuapp.com","firebaseapp.com","000webhostapp.com","blogspot.com","wordpress.com"}
m=BrandMatcher('brand_reference.csv')
rows=[];t0=time.time()
for k in range(1,13):
    month=f"2025-{k:02d}"
    snap=json.load(open(f'historical_snapshots/metadata_{month}.json',encoding='utf-8'))
    s=dt.datetime.strptime(month,'%Y-%m').replace(tzinfo=dt.timezone.utc).timestamp()
    nx=(dt.datetime.strptime(month,'%Y-%m').replace(day=28)+dt.timedelta(days=4)).replace(day=1).replace(tzinfo=dt.timezone.utc).timestamp()
    for d,v in snap.items():
        if s<=v['first_seen']<nx:
            rows.append((month,d,v['first_seen'],v['last_seen'],v['observations'],d in DENY))
    print(month,len(rows),round(time.time()-t0),flush=True)
df=pd.DataFrame(rows,columns=['month','domain','first','last','obs','deny'])
df.to_pickle('cohort_raw.pkl'); print(len(df))
t0=time.time(); sub=df[~df.deny].head(2000)
for d in sub.domain: m.match(d)
print('2000 matches',time.time()-t0)
