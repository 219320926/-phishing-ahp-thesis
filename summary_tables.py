import numpy as np, pandas as pd
from scipy.stats import kendalltau
C=['C1','C2','C3','C4','C5','C6']
S=pd.read_csv('monthly_criteria_series.csv'); F=S[C].values
f0=F.mean(0); w0=f0/f0.sum(); r0=tuple(np.argsort(-w0))
# (a) descriptive table
desc=pd.DataFrame({'mean':F.mean(0),'sd':F.std(0,ddof=1),'min':F.min(0),'max':F.max(0)},index=C)
desc['cv_pct']=desc.sd/desc['mean']*100
desc['min_month']=[S.month[F[:,j].argmin()] for j in range(6)]; desc['max_month']=[S.month[F[:,j].argmax()] for j in range(6)]
desc.to_csv('r_descriptives.csv'); print(desc.round(4))
# (b) designs
def pe(A):
    ev,vec=np.linalg.eig(A); k=ev.real.argmax(); w=np.abs(vec[:,k].real); w/=w.sum(); return w,ev.real[k]
rows=[]
rng=np.random.default_rng(2026)
for p in (0.10,0.20,0.30):
    # Design A: perturb criterion values, rebuild reciprocal matrix
    same=0;taus=[];W=[]
    N=1000
    for _ in range(N):
        f=f0*rng.uniform(1-p,1+p,6); w=f/f.sum(); W.append(w)
        same+= tuple(np.argsort(-w))==r0; taus.append(kendalltau(w0,w)[0])
    W=np.array(W)
    rows.append(dict(design='A: perturb criterion values (reciprocal by construction)',level=p,trials=N,RSI_pct=100*same/N,mean_tau=np.mean(taus),min_tau=np.min(taus),CR_mean=0.0,CR_max=0.0,retained_pct=100.0,**{f'w5_{c}':np.quantile(W[:,j],.05) for j,c in enumerate(C)},**{f'w95_{c}':np.quantile(W[:,j],.95) for j,c in enumerate(C)}))
    # Design B: perturb each pair jointly, enforce reciprocity, recompute eigenvector and CR
    A0=f0[:,None]/f0[None,:]
    same=0;taus=[];crs=[];W=[];keep=0;same_keep=0
    for _ in range(N):
        A=A0.copy()
        for i in range(6):
            for j in range(i+1,6):
                a=A0[i,j]*rng.uniform(1-p,1+p); A[i,j]=a; A[j,i]=1/a
        w,lam=pe(A); cr=((lam-6)/5)/1.24; crs.append(cr); W.append(w)
        s=tuple(np.argsort(-w))==r0; same+=s; taus.append(kendalltau(w0,w)[0])
        if cr<=0.10: keep+=1; same_keep+=s
    W=np.array(W)
    rows.append(dict(design='B: perturb comparison pairs jointly (a_ji = 1/a_ij)',level=p,trials=N,RSI_pct=100*same/N,mean_tau=np.mean(taus),min_tau=np.min(taus),CR_mean=np.mean(crs),CR_max=np.max(crs),retained_pct=100*keep/N,RSI_among_CR_ok_pct=(100*same_keep/keep if keep else np.nan),**{f'w5_{c}':np.quantile(W[:,j],.05) for j,c in enumerate(C)},**{f'w95_{c}':np.quantile(W[:,j],.95) for j,c in enumerate(C)}))
sens=pd.DataFrame(rows); sens.to_csv('r_sensitivity.csv',index=False)
print(sens[['design','level','RSI_pct','mean_tau','min_tau','CR_mean','CR_max','retained_pct']].round(3).to_string())
# flip thresholds
fl=pd.read_csv('g2_flip_thresholds.csv'); print(fl)
# (c) normalisation/orientation
def wv(f): f=np.asarray(f); return f/f.sum()
alt={}
alt['baseline']=wv(f0)
F2=F.copy(); F2[:,3]=1-F2[:,3]; alt['C4 orientation reversed (higher = longer span)']=wv(F2.mean(0))
import itertools
g3=pd.read_csv('g3_preprocessing.csv'); 
# C5 scaling variants
g=pd.read_csv('g3_preprocessing.csv')
print(g[g.group.isin(['C5 scaling','C4 cap','Matcher','Denylist / cohort','Window length'])][['variant','tau','rank_order']])
orient=pd.DataFrame([{'variant':k,**dict(zip(C,v)),'order':' > '.join(C[i] for i in np.argsort(-v)),'tau_vs_baseline':kendalltau(w0,v)[0]} for k,v in alt.items()]); orient.to_csv('r_orientation.csv',index=False); print(orient.round(4))
# (e) strategies
loc=np.array([[0.392,0.486,0.347],[0.126,0.211,0.415],[0.502,0.304,0.238]]); names=['B','C','A']
cw=np.array([w0[0]+w0[1],w0[2]+w0[4],w0[3]+w0[5]]); print('cluster w',cw, loc@cw)
res=[]
def order(sc): return ' > '.join(np.array(names)[np.argsort(-sc)])
res.append(('Reported cluster weights (Table 4.3)',order(loc@cw),*(loc@cw).round(3)))
res.append(('Equal cluster weights (1/3 each)',order(loc@np.ones(3)/3),*(loc@(np.ones(3)/3)).round(3)))
rng=np.random.default_rng(11); cnt={}
for _ in range(10000):
    d=rng.dirichlet([1,1,1]); o=order(loc@d); cnt[o]=cnt.get(o,0)+1
res_cnt=pd.DataFrame([{'cluster weights drawn from Dirichlet(1,1,1)':k,'share_pct':v/100} for k,v in sorted(cnt.items(),key=lambda x:-x[1])]); res_cnt.to_csv('r_strategy_dirichlet.csv',index=False)
# local score perturbation +-0.10
cnt2={}
for _ in range(10000):
    l=np.clip(loc+rng.uniform(-.1,.1,loc.shape),0,1); o=order(l@cw); cnt2[o]=cnt2.get(o,0)+1
pd.DataFrame([{'order':k,'share_pct':v/100} for k,v in sorted(cnt2.items(),key=lambda x:-x[1])]).to_csv('r_strategy_localperturb.csv',index=False)
pd.DataFrame(res,columns=['assumption','order','B','C','A']).to_csv('r_strategy_assumptions.csv',index=False)
print(pd.DataFrame(res)); print(res_cnt); print(sorted(cnt2.items(),key=lambda x:-x[1]))
