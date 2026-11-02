import sys

HasICmp = False
HasSameSign = False
HasGated = False

input = open(sys.argv[1], "r")
for line in input:
    i = line.find(";")
    if i >= 0:
        line = line[:i]
    if "icmp" in line:
        HasICmp = True
    if "samesign" in line:
        HasSameSign = True
    if "%gated" in line:
        HasGated = True

# %gated may only be removed once samesign is gone.
if HasICmp and (HasGated or not HasSameSign):
    sys.exit(0)  # Interesting!

sys.exit(1)
