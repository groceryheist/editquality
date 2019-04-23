import pandas as pd
import itertools
from pull_training_data import load_labels, load_wikis, load_makefile, grep_labelfile
import json
import os

wikis = load_wikis()
makefile = load_makefile()
label_files = list(map(lambda x: grep_labelfile(x, makefile), wikis))

def load_scored_labels(label_file, context):
    filename = "../datasets/scored_labels/{0}".format(os.path.split(label_file)[1])
    labels = (json.loads(l) for l in open(filename,'r'))
    missing_revs = open("missing_revisions.txt",'w')
    for label in labels:
        row = {}
        score = label['score']
        if 'damaging' in label:
            row['true_damaging'] = label['damaging']
        else:
            row['true_damaging'] = None

        if 'goodfaith' in label:
            row['true_goodfaith'] = label['goodfaith']
        else:
            row['true_goodfaith'] = None

        if 'score' in score['damaging']:
            row['prob_damaging'] = score['damaging']['score']['probability']['true']
            row['prob_goodfaith'] = score['goodfaith']['score']['probability']['true']
            row['pred_damaging'] = score['damaging']['score']['prediction']
            row['pred_goodfaith'] =score['goodfaith']['score']['prediction']

        row['rev_id'] = label['rev_id']
        row['wiki'] = context

        yield row

rows = itertools.chain(* [load_scored_labels(label_file, context) for label_file, context in zip(label_files, wikis)])

df_labels = pd.DataFrame(list(rows))
df_labels = df_labels.set_index("rev_id")

df_editors = pd.read_pickle("labeled_newcomers_anons.pickle")

df_editors['rev_id'] = df_editors['revid']
df_editors = df_editors.set_index("rev_id")

# at this point we have the data we need
df_labels = pd.merge(df_labels,df_editors, left_on=["rev_id","wiki"], right_on=["rev_id","wiki"],how='left')

# 
df = df_labels.loc[:,["wiki","rev_id","is_anon","is_newcomer","pred_damaging","pred_goodfaith","prob_damaging","prob_goodfaith","true_damaging","true_goodfaith"]]

missing_scores = df.loc[df.pred_damaging.isna(),:]

df = df.loc[~df.pred_damaging.isna(),:]
df['group'] = 'normal'
df.loc[df.is_anon==True,'group'] = 'anon'
df.loc[df.is_newcomer==True,'group'] = 'newcomer'

df['true_dam'] = df['pred_damaging'] == df['true_damaging']
df['false_pos_dam'] = (df['true_dam'] == False) & (df['pred_damaging'])
df['false_neg_dam'] = df['true_dam'] & (df['pred_damaging'] == False)

df['true_gf'] = df['pred_goodfaith'] == df['true_goodfaith']
df['true_pos_gf'] = df['true_gf'] & df['pred_goodfaith']
df['true_neg_gf'] = (df['true_gf'] == False) & (df['pred_goodfaith'] == False)
df['pred_damaging'] = df['pred_damaging'].astype("double")
df['pred_goodfaith'] = df['pred_goodfaith'].astype("double")
df['wiki'] = df['wiki'].str.replace("wiki","")

rates = df.groupby(["wiki","group"]).mean()
rates['dmg_miscalibration'] = rates['prob_damaging'] - rates['true_dam']
rates['gf_miscalibration'] = rates['prob_goodfaith'] - rates['true_gf'] 

rates['dmg_miscalibration_pred'] = rates['pred_damaging'] - rates['true_dam']
rates['gf_miscalibration_pred'] = rates['pred_goodfaith'] - rates['true_gf'] 

from plotnine import *
theme_set(theme_bw())

p = ggplot(rates.reset_index(),aes(x='wiki',y='dmg_miscalibration',group='group',color='group',fill='group'))
p = p + geom_bar(stat='identity')
p = p + ylab("P(damaging|model) - P(damaging)")
p.save("damaging_miscalibration.png",width=12,height=8,unit='cm')

p = ggplot(rates.reset_index(),aes(x='wiki',y='dmg_miscalibration_pred',group='group',color='group',fill='group'))
p = p + geom_bar(stat='identity',position='dodge')
p = p + ylab("E(P(damaging|model)) - P(damaging)")
p.save("damaging_miscalibration_pred.png",width=12,height=8,unit='cm')

p = ggplot(rates.reset_index(),aes(x='wiki',y='false_pos_dam',group='group',color='group',fill='group'))
p = p + geom_bar(stat='identity',position='dodge')
p = p + ylab("False positive rate (damaging)")
p.save("damaging_fpr.png",width=12,height=8,unit='cm')
p

p = ggplot(rates.reset_index(),aes(x='wiki',y='false_neg_dam',group='group',color='group',fill='group'))
p = p + geom_bar(stat='identity',position='dodge')
p = p + ylab("False negative rate (damaging)")
p.save("damaging_fnr.png",width=12,height=8,unit='cm')
p
