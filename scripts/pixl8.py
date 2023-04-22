from PIL import Image,features
import modules.scripts as scripts
from modules import images
from modules.processing import process_images
from modules.shared import opts
import io
import gradio as gr
import subprocess
import os
import sys

script_dir = scripts.basedir()

#https://github.com/mcychan/nQuantCpp licensed under the GNU General Public License v3.0

class Script(scripts.Script):  
    def __init__(self):
        self.nQuant = 'nQuantCpp.exe'
        self.palette_algos = ['PNN', 'PNNLAB', 'NEU', 'WU', 'EAS', 'SPA', 'DIV', 'DL3', 'MMC','Median', 'Maximum Coverage', 'Octree']
        self.color_palletes = ['Automatic','NES']
    def title(self):
        return "PXL8"
    def show(self, is_img2img):
        return True

    def ui(self, is_img2img):
        with gr.Row():
            dither = gr.Checkbox(True, label="Dither")
            rescale = gr.Checkbox(True, label="Rescale to original size")
            rescale_before = gr.Checkbox(True, label="Rescale before quantize")
        with gr.Row():
            downscale = gr.Slider(minimum=1, maximum=64, step=1, value=8, label="Downscale multiplier")
            color_pal_size = gr.Slider(minimum=0, maximum=256, step=1, value=16, label="Color palette size")
        if features.check_feature("libimagequant"):
            self.palette_algos.insert(0, "libimagequant")
        palette_algo = gr.Radio(choices=self.palette_algos, value=self.palette_algos[0], label='Palette Extraction Algorithm')

        #add dropdown for color palletes
        #custom_palette = gr.Dropdown(choices=self.color_palletes, label="Custom Palette")
        
        return [downscale,rescale,rescale_before,color_pal_size,palette_algo,dither]

    def run(self, p, downscale,rescale,rescale_before,color_pal_size,palette_algo,dither):        
        def process(im):
            isDither = 1 if dither else 0
            isSmart = 1 if palette_algo in self.palette_algos[:9] else 0
            #isCustomPalette = 1 if custom_palette != "None" else 0
            temp = os.path.join(script_dir,"temp.png")
            out_width, out_height = im.size
            sample_width = int(out_width / downscale)
            sample_height = int(out_height / downscale)
            if rescale_before:
                work = im.resize((sample_width, sample_height), Image.NEAREST)
            else:
                work = im
            if color_pal_size != 0:
                if isSmart == 0:
                    method = Image.Quantize.MEDIANCUT if palette_algo == 'Median' else Image.Quantize.MAXCOVERAGE if palette_algo == 'Maximum Coverage' else Image.Quantize.FASTOCTREE if palette_algo == 'Octree' else Image.Quantize.LIBIMAGEQUANT
                    work = work.convert("RGB").quantize(colors=int(color_pal_size), method=method, dither=Image.Dither.FLOYDSTEINBERG if isDither else 0)
                else:
                    work = work.convert("RGB")
                    work.save(temp)
                    run = subprocess.run([os.path.join(script_dir, self.nQuant), temp, f"/m ",str(color_pal_size), f"/a ",palette_algo, "/d ","y" if isDither==1 else "n",], stdout=subprocess.DEVNULL)
                    s_t = os.path.join(script_dir,f"temp-{palette_algo}quant{color_pal_size}.png")
                    #open s_t without holding it open
                    work = Image.open(s_t).convert("RGB")
                    os.remove(s_t)
                    os.remove(temp)
            if rescale_before == False:
                work = work.resize((sample_width, sample_height), Image.NEAREST)
            if rescale:
                work = work.resize((out_width, out_height), Image.NEAREST)
            return work
        out = process_images(p)
        for i in range(len(out.images)):
            out.images[i] = process(out.images[i])
            if opts.samples_format == "png" or opts.samples_format == "jpg" or opts.samples_format == "jpeg":
                out.images[i] = out.images[i].convert('RGB')
            images.save_image(out.images[i], p.outpath_samples, "", out.seed + i, out.prompt, opts.samples_format, info= out.info, p=p)
        return out