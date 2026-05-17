# SVG DSL Examples

> **For deep infographics** (build pipelines, dense system diagrams on
> the `svg-infographic-full` layout), see
> [examples-deep.md](examples-deep.md) — Yocto build pipelines and other
> richer compositions using the extended primitive set.

## Simple bar chart

```
canvas 600x400
rect bg 0,0 600x400 paper
text t1 300,30 title "Q1 Revenue by Region"
axis x1 horizontal 80,350 480 "EMEA,APAC,AMER,LATAM"
bar b1 120,150 80x200 primary value:"$85k"
bar b2 220,200 80x150 secondary value:"$62k"
bar b3 320,100 80x250 success value:"$98k"
bar b4 420,250 80x100 tertiary value:"$41k"
legend lg 240,380 primary:"EMEA" secondary:"APAC" success:"AMER" tertiary:"LATAM"
```

## Stat card grid

```
canvas 600x300
rect bg 0,0 600x300 paper
rect c1 20,40 180x100 surface-2
text k1 40,75  title "12"
text l1 40,110 body "Launches"
rect c2 220,40 180x100 surface-2
text k2 240,75  title "3"
text l2 240,110 body "New customers"
rect c3 420,40 180x100 surface-2
text k3 440,75  title "$4.2M"
text l3 440,110 body "ARR"
```

## Annotated chart with so-what

```
canvas 800x500
rect bg 0,0 800x500 paper
text t1 400,40 title "AMER pulled +18% YoY while LATAM softened"
axis x1 horizontal 100,420 600 "EMEA,APAC,AMER,LATAM"
bar b1 140,200 100x220 primary value:"$85k"
bar b2 290,280 100x140 secondary value:"$62k"
bar b3 440,150 100x270 success value:"$98k"
bar b4 590,320 100x100 tertiary value:"$41k"
text sw 400,470 detail "AMER acceleration is the lever; protect it in Q2 plan"
```
