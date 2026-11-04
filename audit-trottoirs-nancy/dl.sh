cd "$1"
python3 - <<'P' > tiles.txt
x0,x1,y0,y1=6.134,6.2135,48.666,48.7105
nx,ny=8,8
for i in range(nx):
  for j in range(ny):
    a=x0+(x1-x0)*i/nx; b=x0+(x1-x0)*(i+1)/nx; c=y0+(y1-y0)*j/ny; d=y0+(y1-y0)*(j+1)/ny
    print(f"{i}_{j} {a:.5f},{c:.5f},{b:.5f},{d:.5f}")
P
while read n bb; do
  [ -s t_$n.osm ] && grep -q '</osm>' t_$n.osm && continue
  for k in 1 2 3 4; do
    code=$(curl -sS -m 180 -A "osm-audit-script" -o t_$n.osm -w "%{http_code}" "https://api.openstreetmap.org/api/0.6/map?bbox=$bb")
    [ "$code" = 200 ] && break; echo "$n $code"; sleep $((k*3))
  done
done < tiles.txt
echo done
