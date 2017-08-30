import sys
import os

args = sys.argv

#column's index
index = int(args[1])

#read file
dataEnv = os.environ.get('GRAPE_DATASET_DIR')
f = open(os.path.join(dataEnv, 'data', args[2]), 'r').read().split('\n')

#output list
output_list = []

for i in range(0, len(f)):
	f[i] = f[i].split()
	if len(f[i]) > 0:
		output_list.append(float(f[i][index]))

#sort
output_list = sorted(output_list)
print output_list

#write file, outdir default=model
outdir = 'model'
if not os.path.exists(outdir):
    os.mkdir(outdir)
dst = os.path.join(outdir, 'ans1.txt')
o = open(dst, 'w')
for i in range(0, len(output_list)-1):
	o.write(str(output_list[i]) + ',')
o.write(str(output_list[len(output_list)-1]))
o.close()	
