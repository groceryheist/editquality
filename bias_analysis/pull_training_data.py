#!/usr/bin/env python3
import re
import time
import subprocess
import os
import shutil
import mwapi
import json
from ores.utilities.score_revisions import run as call_ores
from revscoring.extractors import api
from revscoring.utilities.extract import extract, ConfiguredExtractor
import yamlconf
from revscoring.dependencies import Dependent
import editquality.feature_lists
from concurrent.futures import ThreadPoolExecutor
import itertools

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

def score_labels(labels,context,label_file, overwrite = False):
    if not os.path.exists("../datasets/scored_labels"):
        os.makedirs("../datasets/scored_labels")

    output_filename = "../datasets/scored_labels/{0}".format(os.path.split(label_file)[1])

    if os.path.exists(output_filename) and overwrite == False:
        return

    ores_host = "https://ores.wikimedia.org/"
    user_agent = "Ores bias analysis project by Nate TeBlunthuis <groceryheist@uw.edu>"

    output_file = open(output_filename,'w')

    call_ores(ores_host,
              user_agent,
              context,
              model_names = ["damaging","goodfaith"],
              parallel_requests=4,
              retries=2,
              input=labels,
              output=output_file,
              batch_size=50,
              verbose=True)

    output_file.close()

# get the features
def extract_features(label_file,context):
    rev_ids = [json.loads(label) for label in load_labels(label_file)]
    
    session = mwapi.Session(
        host= "https://{0}.wikipedia.org".format(
            context.replace("wiki","")),
        user_agent="Ores bias analysis project by Nate TeBlunthuis <groceryheist@uw.edu>")

    dependent_names = ["editquality.feature_lists.{0}.damaging".format(context),
                  "editquality.feature_lists.{0}.goodfaith".format(context)]
    dependents = []
    for dependent_path in dependent_names:
        dependent_or_list = yamlconf.import_path(dependent_path)
        if isinstance(dependent_or_list, Dependent):
            dependents.append(dependent_or_list)
        else:
            dependents.extend(dependent_or_list)

    extractor = api.Extractor(session)
    features = extract(dependents, rev_ids, extractor,extractors=os.cpu_count() - 1)
    return features


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def get_editor_traits(labels, context, output):
    print(context)
    rev_ids = [json.loads(label)['rev_id'] for label in labels]
    # special case for wikidata, esbooks

    if context == "wikidatawiki":
        host= "https://wikidata.org".format(context.replace("wiki",""))
    elif context == "eswikibooks":
        host= "https://es.wikibooks.org".format(context.replace("wiki",""))
    else:
        host= "https://{0}.wikipedia.org".format(context.replace("wiki",""))

    user_agent="Ores bias analysis project by Nate TeBlunthuis <groceryheist@uw.edu>"
    session = mwapi.Session(host,user_agent)

    batches = grouper(rev_ids, 50)

    def table_results(batch, context):
        row = {}
        resultset = batch['query']['pages']
        for _, page_id in enumerate(resultset):
            result = resultset[page_id]
            row['ns'] = result['ns']
            row['title'] = result['title']
            row['pageid'] = result['pageid']
            row['wiki'] = context
            revisions = result['revisions']
            for rev in revisions:
                row['revid'] = rev['revid']
                row['parentid'] = rev['parentid']
                if 'user' in rev:
                    row['user'] = rev['user']
                    row['userid'] = rev['userid']
                else:
                    row['user'] = None
                    row['userid'] = None
                yield row

    def keep_trying(call, *args, **kwargs):
        try:
            result = call(*args, **kwargs)
            return result
        except Exception as e:
            print(e)
            time.sleep(1)
            return keep_trying(call, *args, **kwargs)

    with ThreadPoolExecutor(100) as executor:
        # get revision metadata
        revision_batches = executor.map(lambda batch:keep_trying(call=session.get, action="query", prop='revisions', rvprop=['ids','user','userid'], revids=batch), batches)

        badrevids = []
        rows = []
        for batch in revision_batches:
            if 'badrevids' in batch['query']:
                badrevids.append(batch['query']['badrevids'])
            for row in table_results(batch, context):
                out_row = '\t'.join([str(row[key]) for key in out_schema])
                output.write(out_row + '\n')


if __name__ == "__main__":
    wikis = load_wikis()
    makefile = load_makefile()
    label_files = list(map(lambda x: grep_labelfile(x, makefile), wikis))
    list(map(download_labels,label_files))
    [score_labels(load_labels(label_file),wiki,label_file) for wiki,label_file in zip(wikis,label_files)]
    
    with open("editor_revisions.tsv",'w') as label_metadata_temp1:
        out_schema = ['wiki','ns','pageid','title','revid','parentid','user','userid']
        print("collecting userids")
        label_metadata_temp1.write('\t'.join(out_schema))
        
        for label_file, context in zip(label_files,wikis):
            labels = load_labels(label_file)
            get_editor_traits(labels,context,label_metadata_temp1)
    
    
# next step
