import os
import re

# path to output of mangrovegranules.py
outfile = "/Users/fcseidl/EarthLab-local/BioExtremes/slurm-3597129.out"

# get urls of granules touching mangrove regions
urls = []
with open(outfile) as reader:
    exp = "[\d*], True, (.*).xml$"
