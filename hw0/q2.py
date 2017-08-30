from PIL import Image
import sys
import os

dataEnv = os.environ.get('GRAPE_DATASET_DIR')
im = Image.open(os.path.join(dataEnv, 'data', sys.argv[1]))
rgb_im = im.convert('RGB')

#w, h
width, height = im.size

# #save Image
# output_image = Image.new("RGB", (width, height), "white")

# #turn around the image
# for w in range(0, width):
# 	for h in range(0, height):
# 		#r, g, b = rgb_im.getpixel((w, h))
# 		rgb = im.getpixel((w, h))
# 		output_image.putpixel((width-w-1, height-h-1), rgb)
# output_image.save("ans2.png")

outdir = 'model'
if not os.path.exists(outdir):
    os.mkdir(outdir)
dst = os.path.join(outdir, 'ans2.png')

out = im.transpose(Image.ROTATE_180)
out.save(dst)
