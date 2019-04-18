#!/usr/bin/env python3
import re
import subprocess
import os
import shutil
import mwapi
import json
from ores.utilities.score_revisions import run as call_ores

def load_wikis():
    lines = open("rcfilters_enabled.csv",'r')
    wikis = [line.split(',')[0] for line in lines]
    wikis = [wiki for wiki in wikis if wiki != "Wiki"]

    # simple wiki uses the same models and labels as english wikipedia
    wikis = [wiki for wiki in wikis if wiki != "simplewiki"]
    return wikis
    
def load_makefile():
    with open("../Makefile",'r') as makefile1:
        with open("../Makefile.manual",'r') as makefile2:
            makefile = makefile1.read() + '\n' + makefile2.read()
    return makefile
                           
def grep_labelfile(wiki, makefile):
    humanlabel_re_format = r"datasets/{0}\.human_labeled_revisions\.(.*)k_(.*)\.json:.*"
    # find candidate human labeled revisions
    humanlabel_re = re.compile(humanlabel_re_format.format(wiki))
    # choose the best match
    # choose the human labeled revisions with the largest N
    # and the most recent
    matches = list(humanlabel_re.finditer(makefile))
    if len(matches) == 0:
        print("found no matches for {0}".format(wiki))
        return None

    max_n = max(int(match.groups()[0]) for match in matches)
    max_n_match = [match for match in matches if int(match.groups()[0]) == max_n]

    latest_date = max(int(match.groups()[1]) for match in max_n_match)
    latest_date_match = [match for match in max_n_match if int(match.groups()[1]) == latest_date]
    if len(latest_date_match) > 1:
        print("too many matches {1} for {0}".format(wiki,latest_date_match))
        return None
    else:
        print("found match {0} for {1}".format(latest_date_match[0],wiki))
        match = latest_date_match[0]
        label_file = makefile[match.start():match.end()-1]
        return label_file
        
def download_labels(label_file):
    os.chdir("..")
    try: 
        subprocess.call(["make",label_file])
    except Exception as e:
        print(e)
    os.chdir("bias_analysis")

def load_labels(label_file):
    return open("../{0}".format(label_file))

def score_labels(labels,context,label_file):
    ores_host = "https://ores.wikimedia.org/"
    user_agent = "Ores bias analysis project by Nate TeBlunthuis (groceryheist)"
    output_file = "../scored_labels/{0}".format(label_file)
    call_ores(ores_host, user_agent, context, model_names = ["damaging","goodfaith","reverted"],
              parallel_requests=3,retries=2,input=labels,output=output_file,batch_size=50,verbose=True)

if __name__ == "__main__":
    wikis = load_wikis()
    makefile = load_makefile()
    label_files = list(map(lambda x: grep_labelfile(x, makefile), wikis))
    list(map(download_labels,label_files))
    [score_labels(load_labels(label_file),wiki,label_file) for wiki,label_file in zip(wikis,label_files)]
    
    
# next step
