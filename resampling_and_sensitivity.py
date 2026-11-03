import re, csv, json, datetime as dt, itertools, numpy as np, pandas as pd
from scipy.stats import kendalltau, spearmanr
from rapidfuzz.distance import Levenshtein
C=['C1','C2','C3','C4','C5','C6']
S=pd.read_csv('monthly_criteria_series.csv'); F=S[C].values
def w_of(f): f=np.asarray(f,float); return f/f.sum()   # ratio-AHP principal eigenvector == f/sum(f)
def ahp_check(f):
    f=np.asarray(f,float); M=f[:,None]/f[None,:]; ev=np.linalg.eigvals(M).real.max(); return (ev-6)/5/1.24
base=w_of(F.mean(0)); print('baseline',dict(zip(C,base.round(4))),'CR',round(ahp_check(F.mean(0)),12))
def tau(a,b): return kendalltau(a,b)[0]
def ranks(w): return (-w).argsort().argsort()+1
out={}
# ---------- GROUP 1
rows=[]
n=12
for B in [200,500,1000,5000]:
    lo=[];hi=[];sd=[]
    for seed in range(30):
        rng=np.random.default_rng(seed); idx=rng.integers(0,n,(B,n))
        W=np.array([w_of(F[i].mean(0)) for i in idx])
        lo.append(np.quantile(W,.025,0));hi.append(np.quantile(W,.975,0));sd.append(W.std(0,ddof=1))
    lo,hi,sd=map(np.array,(lo,hi,sd))
    for j,c in enumerate(C):
        rows.append(dict(B=B,criterion=c,ci_lo=lo[:,j].mean(),ci_hi=hi[:,j].mean(),ci_width=(hi-lo)[:,j].mean(),
          mc_sd_of_width=(hi-lo)[:,j].std(ddof=1),mc_sd_of_lo=lo[:,j].std(ddof=1),mc_sd_of_hi=hi[:,j].std(ddof=1),boot_sd=sd[:,j].mean()))
g1=pd.DataFrame(rows); g1.to_csv('g1_bootstrap_convergence.csv',index=False)
# jackknife
J=np.array([w_of(np.delete(F,i,0).mean(0)) for i in range(n)])
jse=np.sqrt((n-1)/n*((J-J.mean(0))**2).sum(0))
jk=pd.DataFrame({'criterion':C,'weight':base,'jackknife_se':jse,'jk_min':J.min(0),'jk_max':J.max(0)})
jk['boot_sd_B1000']=g1[g1.B==1000].set_index('criterion').loc[C,'boot_sd'].values
jk.to_csv('g1_jackknife.csv',index=False)
infl=pd.DataFrame(J-base,columns=C); infl.insert(0,'left_out',S.month); infl['tau_vs_base']=[tau(base,j) for j in J]
infl['top1']=[C[j.argmax()] for j in J]; infl.to_csv('g1_leave_one_month_out.csv',index=False)
# block bootstrap (moving blocks)
bb=[]
for L in [1,2,3,4]:
    rng=np.random.default_rng(7); W=[]
    for _ in range(2000):
        idx=[]
        while len(idx)<n:
            s=rng.integers(0,n-L+1); idx+=list(range(s,s+L))
        W.append(w_of(F[idx[:n]].mean(0)))
    W=np.array(W)
    for j,c in enumerate(C): bb.append(dict(block_len=L,criterion=c,sd=W[:,j].std(ddof=1),ci_lo=np.quantile(W[:,j],.025),ci_hi=np.quantile(W[:,j],.975)))
pd.DataFrame(bb).to_csv('g1_block_bootstrap.csv',index=False)
# rank probability from bootstrap B=5000
rng=np.random.default_rng(42); idx=rng.integers(0,n,(5000,n)); W=np.array([w_of(F[i].mean(0)) for i in idx])
R=np.array([ranks(w) for w in W]); rp=pd.DataFrame({c:[(R[:,j]==r).mean() for r in range(1,7)] for j,c in enumerate(C)},index=[f'rank{r}' for r in range(1,7)])
rp.to_csv('g1_rank_probability.csv'); pair=(W[:,4]>W[:,3]).mean(); print('P(C5>C4)',pair)
# ---------- GROUP 2
rows=[]
for j,c in enumerate(C):
    for p in [-.3,-.2,-.1,.1,.2,.3]:
        f=F.mean(0).copy(); f[j]*=1+p; w=w_of(f)
        rows.append(dict(criterion=c,perturb=p,weight=w[j],base_weight=base[j],rel_change=w[j]/base[j]-1,
          tau=tau(base,w),rank_before=ranks(base)[j],rank_after=ranks(w)[j],rank_changed=int((ranks(w)!=ranks(base)).any()),top1=C[w.argmax()]))
g2=pd.DataFrame(rows); g2.to_csv('g2_single_perturbation.csv',index=False)
# smallest relative perturbation flipping a rank (each criterion)
flip=[]
for j,c in enumerate(C):
    res={}
    for sgn in (1,-1):
        for p in np.arange(0.001,3,0.001):
            f=F.mean(0).copy(); f[j]*=1+sgn*p
            if p>=1 and sgn==-1: break
            if (ranks(w_of(f))!=ranks(base)).any(): res[sgn]=p;break
    flip.append(dict(criterion=c,up=res.get(1),down=res.get(-1)))
pd.DataFrame(flip).to_csv('g2_flip_thresholds.csv',index=False)
rows=[]
for sd in [.1,.2,.3]:
    rng=np.random.default_rng(1); T=[];same=[];top2=[];top1=[]
    for _ in range(10000):
        f=F.mean(0)*np.exp(rng.normal(0,sd,6)); w=w_of(f)
        T.append(tau(base,w)); same.append((ranks(w)==ranks(base)).all()); top1.append(w.argmax()==base.argmax())
        top2.append(set(np.argsort(-w)[:2])==set(np.argsort(-base)[:2]))
    rows.append(dict(noise_sd=sd,mean_tau=np.mean(T),p05_tau=np.quantile(T,.05),ranking_identical=np.mean(same),top1_kept=np.mean(top1),top2_set_kept=np.mean(top2)))
pd.DataFrame(rows).to_csv('g2_joint_noise.csv',index=False)
# ---------- GROUP 4
def entropy_w(X):
    P=X/X.sum(0); k=1/np.log(len(X)); E=-k*np.nansum(np.where(P>0,P*np.log(P),0),0); d=1-E; return d/d.sum()
def critic_w(X):
    Z=(X-X.min(0))/(X.max(0)-X.min(0)); s=Z.std(0,ddof=1); r=np.corrcoef(Z.T); I=s*(1-r).sum(0); return I/I.sum()
def equal_w(X): return np.ones(6)/6
methods={'ratio_AHP':lambda X:w_of(X.mean(0)),'equal':equal_w,'entropy':entropy_w,'CRITIC':critic_w,
 'AHP_median':lambda X:w_of(np.median(X,0))}
rows=[];wts={}
for m,fn in methods.items():
    w=fn(F);wts[m]=w
    rows.append(dict(method=m,**{c:v for c,v in zip(C,w)}))
pd.DataFrame(rows).to_csv('g4_weights.csv',index=False)
rows=[]
for m,fn in methods.items():
    rng=np.random.default_rng(42); Wb=np.array([fn(F[rng.integers(0,n,n)]) for _ in range(2000)])
    Rb=np.array([ranks(w) for w in Wb]); w0=wts[m]
    rows.append(dict(method=m,tau_vs_ratioAHP=tau(wts['ratio_AHP'],w0),spearman_vs_ratioAHP=spearmanr(wts['ratio_AHP'],w0)[0],
      mean_ci_width=np.mean(np.quantile(Wb,.975,0)-np.quantile(Wb,.025,0)),
      mean_boot_sd=Wb.std(0,ddof=1).mean(),
      rank_identical_to_own_pointrank=np.mean((Rb==ranks(w0)).all(1)),
      boot_tau_to_own_point_mean=np.mean([tau(w0,w) for w in Wb]),top1_stability=np.mean(Wb.argmax(1)==w0.argmax())))
pd.DataFrame(rows).to_csv('g4_comparison.csv',index=False)
# month-by-month ranking agreement: ratio-AHP (per-month f) vs equal-weights (trivial) -- agreement of per-month ranking across methods using window of 3 months
rows=[]
for i in range(n):
    a=w_of(F[i]); rows.append(dict(month=S.month[i],tau_month_vs_annual=tau(a,base),top1=C[a.argmax()]))
pd.DataFrame(rows).to_csv('g4_monthly_ranking.csv',index=False)
# ---------- GROUP 3 (needs raw)
df=pd.read_pickle('cohort_raw.pkl')
DENY=set(df[df.deny].domain)
from brand_matcher import _tokenize
refs=[]
with open('brand_reference.csv',newline='') as f:
    for r in csv.DictReader(f): refs.append((r['brand'],r['sector'],[k.strip().lower() for k in r['keywords'].split('|')]))
def make_match(brands,fuzzy=True,minlen=6,budget=lambda L:1 if L<=7 else 2):
    def m(domain):
        d=domain.lower()
        for b,s,kws in brands:
            for kw in kws:
                if kw in d: return b,s
        if not fuzzy: return None,None
        toks=_tokenize(d);best=0;bb=None;bs=None
        for b,s,kws in brands:
            for kw in kws:
                if len(kw)<minlen: continue
                bud=budget(len(kw))
                for t in toks:
                    if abs(len(t)-len(kw))>bud: continue
                    dist=Levenshtein.distance(t,kw,score_cutoff=bud)
                    if dist<=bud:
                        sc=1-dist/len(kw)
                        if sc>best: best,bb,bs=sc,b,s
        return bb,bs
    return m
dom=df.domain.values; mon=df.month.values
parts=[d.split('.') for d in dom]
ip=np.array([1 if all(p.isdigit() for p in ps if p) and len(ps)==4 else 0 for ps in parts])
sub=np.array([max(0,len(ps)-2) for ps in parts])
deceptive=((ip==1)|(sub>2)).astype(float)
span_d=np.maximum((df['last'].values-df['first'].values)/86400,0.5); pres=np.minimum(df.obs.values/(span_d*2),1.0)
span_h=(df['last'].values-df['first'].values)/3600
cl=open('upstream_changelog/changelog.md',encoding='utf-8').read().split('### ')[1:]
madd={}
for e in cl:
    ls=e.strip().splitlines(); ts=re.sub(r'\+00:00$','',ls[0].replace(' Changelog','').strip())
    try: t=dt.datetime.strptime(ts,'%Y-%m-%d %H:%M:%S.%f')
    except ValueError: continue
    for l in ls[1:]:
        l=l.strip().lstrip('- ').strip()
        if l.startswith('Adding'):
            x=re.findall(r'\d+',l)
            if x: madd[t.strftime('%Y-%m')]=madd.get(t.strftime('%Y-%m'),0)+int(x[0])
months=list(S.month); add=np.array([madd.get(m,0) for m in months],float)
matchcache={}
def compute(brands=refs,matcher=None,deny=True,cap='p95',c5='max',window=12,minobs=0,nref=None,sectorK=None):
    matcher=matcher or make_match(brands)
    key=id(matcher)
    if key not in matchcache:
        matchcache[key]=[matcher(d) for d in dom]
    mm=matchcache[key]
    nref=nref or len(brands)
    keep=(~df.deny.values if deny else np.ones(len(df),bool))&(df.obs.values>=minobs)
    # cap
    allsp=span_h[keep]
    capv={'p95':4422,'p90':np.quantile(allsp,.90),'p99':np.quantile(allsp,.99),'max':allsp.max(),'p75':np.quantile(allsp,.75)}[cap] if isinstance(cap,str) else cap
    r=[]
    for k,m in enumerate(months[:window]):
        sel=keep&(mon==m); n_=sel.sum()
        if n_==0: r.append([np.nan]*6); continue
        idx=np.where(sel)[0]
        matched=[mm[i] for i in idx if mm[i][0]]
        c1=deceptive[idx].mean(); c2=pres[idx].mean(); c3=len({b for b,_ in matched})/nref
        c4=max(0,1-min(span_h[idx].mean(),capv)/capv)
        c6=(sum(1 for _,s in matched if s=='Financial Services')/len(matched)) if matched else 0
        r.append([c1,c2,c3,c4,np.nan,c6])
    r=np.array(r)
    a=add[:window]
    r[:,4]={'max':a/a.max(),'minmax':(a-a.min())/(a.max()-a.min()),'mean':a/a.mean()/2,'share':a/a.sum()*window/2,'log':np.log1p(a)/np.log1p(a.max())}[c5]
    return r
chk=compute(); print('reproduction max abs diff vs published series:',np.nanmax(np.abs(chk-F)))
variants=[]
def add_v(group,name,**kw): variants.append((group,name,kw))
add_v('baseline','baseline')
for cap in ['p75','p90','p99','max']: add_v('C4 cap',f'cap={cap}',cap=cap)
for c5 in ['minmax','mean','share','log']: add_v('C5 scaling',f'C5={c5}',c5=c5)
for nm,fz,ml,bud in [('no fuzzy',False,6,None),('budget 1 all',True,6,lambda L:1),('budget 2 all',True,6,lambda L:2),('min kw len 5',True,5,None),('min kw len 8',True,8,None),('min kw len 4',True,4,None)]:
    kw=dict(matcher=make_match(refs,fz,ml,bud) if bud else make_match(refs,fz,ml)); add_v('Matcher',nm,**kw)
for sec in sorted({s for _,s,_ in refs}):
    br=[r for r in refs if r[1]!=sec]; add_v('Brand list (drop sector)',f'drop {sec} ({len(refs)-len(br)} brands)',brands=br,matcher=make_match(br),nref=len(br))
rng=np.random.default_rng(5)
for rep in range(5):
    keep_idx=rng.choice(len(refs),int(.8*len(refs)),replace=False); br=[refs[i] for i in keep_idx]
    add_v('Brand list (random 80%)',f'random 80% #{rep+1}',brands=br,matcher=make_match(br),nref=len(br))
add_v('Denylist / cohort','no denylist',deny=False)
add_v('Denylist / cohort','require obs>=2',minobs=2)
add_v('Denylist / cohort','require obs>=5',minobs=5)
for w in [6,9]: add_v('Window length',f'first {w} months',window=w)
rows=[]
for g,nm,kw in variants:
    X=compute(**kw); 
    # weights from mean over available months
    wv=w_of(np.nanmean(X,0)); rows.append(dict(group=g,variant=nm,**{c:v for c,v in zip(C,wv)},tau=tau(base,wv),rank_order=' > '.join(C[i] for i in np.argsort(-wv)),
        max_abs_change=np.abs(wv-base).max(),top1=C[wv.argmax()]))
    print(g,nm,round(rows[-1]['tau'],3),rows[-1]['rank_order'],flush=True)
g3=pd.DataFrame(rows); g3.to_csv('g3_preprocessing.csv',index=False)
print(len(variants),'variants')
