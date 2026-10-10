import argparse,csv,pathlib,re,subprocess,sys

p=argparse.ArgumentParser()
p.add_argument("--out",default="results/paired-hardware-simulation")
p.add_argument("--seconds",type=int,default=5)
p.add_argument("--size-kb",type=int,default=1024)
p.add_argument("--seed",type=int,default=11)
p.add_argument("--repeats",type=int,default=3)
p.add_argument("--cpu",type=int,default=2)
a=p.parse_args()

out=pathlib.Path(a.out); out.mkdir(parents=True,exist_ok=True)
patterns=["sequential","strided","random","hash","transition"]
rows=[]

def perf_values(f):
    d={}
    for line in pathlib.Path(f).read_text(errors="ignore").splitlines():
        x=line.split(",")
        if len(x)>=3:
            try: d[x[2]]=float(x[0])
            except: pass
    r=d.get("cache-references",0); m=d.get("cache-misses",0)
    d["perf_miss_rate_pct"]=100*m/r if r else ""
    return d

for pat in patterns:
  for n in range(1,a.repeats+1):
    seed=a.seed+n-1
    base=[sys.executable,"workloads/pattern_workload.py",
          "--pattern",pat,"--seconds",str(a.seconds),
          "--size-kb",str(a.size_kb),"--seed",str(seed)]
    tag=f"{pat}-run{n}"
    pf=out/(tag+".perf.csv")
    cf=out/(tag+".cachegrind.out")

    subprocess.run(["sudo","perf","stat","-x,", "-o",str(pf),
                    "-e","cycles,instructions,cache-references,cache-misses",
                    "taskset","-c",str(a.cpu)]+base,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

    subprocess.run(["valgrind","--tool=cachegrind","--cache-sim=yes",
                    f"--cachegrind-out-file={cf}"]+base,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

    text=""
    if cf.exists():
        q=subprocess.run(["cg_annotate",str(cf)],capture_output=True,text=True)
        text=q.stdout

    nums=[]
    for line in text.splitlines():
        if "PROGRAM TOTALS" in line:
            nums=[int(x.replace(",","")) for x in
                  re.findall(r"[0-9][0-9,]*",line)]
            break

    sim_rate=""
    if len(nums)>=4 and nums[0]+nums[1]>0:
        sim_rate=100*(nums[2]+nums[3])/(nums[0]+nums[1])

    row={"pattern":pat,"run":n}
    row.update(perf_values(pf))
    row["cachegrind_miss_rate_pct"]=sim_rate
    rows.append(row)

fields=sorted({k for r in rows for k in r})
with open(out/"paired-summary.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

print("PAIRED_ROWS="+str(len(rows)))
print("SUMMARY="+str(out/"paired-summary.csv"))
