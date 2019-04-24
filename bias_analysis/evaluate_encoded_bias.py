#!/usr/bin/env python3
from plotnine import *
import pandas as pd
import itertools
from get_labels import load_labels, load_wikis, load_makefile, grep_labelfile
import json
import os
import numpy as np

wikis = load_wikis()
makefile = load_makefile()
label_files = list(map(lambda x: grep_labelfile(x, makefile), wikis))

def load_scored_labels(label_file, context):
    filename = "../datasets/scored_labels/{0}".format(
        os.path.split(label_file)[1])
    labels = (json.loads(l) for l in open(filename, 'r'))
    missing_revs = open("missing_revisions.txt", 'w')
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
            # These are the labels based on the default threshholds
            # But for fair comparison between the different wikis
            # I chose to choose threshholds with fpr ~= fnr
            # row['pred_damaging'] = score['damaging']['score']['prediction']
            # row['pred_goodfaith'] =score['goodfaith']['score']['prediction']

        row['rev_id'] = label['rev_id']
        row['wiki'] = context

        yield row


# just use grid search to choose a threshhold
# that maximizes accuracy
def choose_threshhold(true_col, prob_col, n=500):
    ts = np.arange(0, n + 1) / n

    def acc(t):
        tpr = np.mean((prob_col >= t) & (true_col == True))
        tnr = np.mean((prob_col < t) & (true_col == False))
        return (tpr + tnr)
    t = np.argmax(np.abs(list(map(acc, ts))))

    return (ts[t], acc(t))


def pred_wiki(df, wiki, model='damaging'):
    prob_col = df.loc[df.wiki == wiki, "prob_{0}".format(model)]
    true_col = df.loc[df.wiki == wiki, "true_{0}".format(model)]
    t, acc = choose_threshhold(true_col, prob_col)
    df.loc[df.wiki == wiki, 'pred_{0}'.format(model)] = (prob_col > t)
    return (df, acc)


def gen_preds(df, model='damaging'):
    wikis = set(df.wiki)
    accs = []
    for wiki in wikis:
        df, acc = pred_wiki(df, wiki, model)
        accs.append(acc)

    return (df, accs, wikis)


rows = itertools.chain(* [load_scored_labels(label_file, context)
                          for label_file, context in zip(label_files, wikis)])
df_labels = pd.DataFrame(list(rows))
df_labels = df_labels.set_index("rev_id")

df_editors = pd.read_pickle("labeled_newcomers_anons.pickle")

df_editors['rev_id'] = df_editors['revid']
df_editors = df_editors.set_index("rev_id")
# at this point we have the data we need
df_labels = pd.merge(df_labels, df_editors,
                     left_on=["rev_id", "wiki"],
                     right_on=["rev_id", "wiki"],
                     how='left')
#
df = df_labels.loc[:, ["wiki",
                       "revid",
                       "is_anon",
                       "is_newcomer",
                       "pred_damaging",
                       "pred_goodfaith",
                       "prob_damaging",
                       "prob_goodfaith",
                       "true_damaging",
                       "true_goodfaith"]]

missing_scores = df.loc[df.prob_damaging.isna(), :]
df = df.loc[~df.prob_damaging.isna(), :]

df, acc, wikis = gen_preds(df,model='damaging')
print(list(zip(wikis, acc)))

df, acc, wikis = gen_preds(df,model='goodfaith')
print(list(zip(wikis, acc)))

df['group'] = 'normal'
df.loc[df.is_anon == True, 'group'] = 'anon'
df.loc[df.is_newcomer == True, 'group'] = 'newcomer'

df['true_dmg'] = df['pred_damaging'] == df['true_damaging']
df['false_pos_dmg'] = (df['true_dmg'] == False) & (df['pred_damaging'])
df['false_neg_dmg'] = df['true_dmg'] & (df['pred_damaging'] == False)

df['true_gf'] = df['pred_goodfaith'] == df['true_goodfaith']
df['true_pos_gf'] = df['true_gf'] & df['pred_goodfaith']
df['true_neg_gf'] = (df['true_gf'] == False) & \
    (df['pred_goodfaith'] == False)

df['pred_damaging'] = df['pred_damaging'].astype("double")
df['pred_goodfaith'] = df['pred_goodfaith'].astype("double")
df['wiki'] = df['wiki'].str.replace("wiki", "")

rates = df.groupby(["wiki", "group"]).mean()
rates['dmg_miscalibration'] = rates['prob_damaging'] - rates['true_dmg']
rates['gf_miscalibration'] = rates['prob_goodfaith'] - rates['true_gf']

rates['dmg_miscalibration_pred'] = rates['pred_damaging'] - rates['true_dmg']
rates['gf_miscalibration_pred'] = rates['pred_goodfaith'] - rates['true_gf']

theme_set(theme_bw())

rates = rates.reset_index()
p = ggplot(rates, aes(x='wiki', y='dmg_miscalibration',
                      group='group', color='group', fill='group'))
p = p + geom_bar(stat='identity', position='dodge')
p = p + ylab("P(damaging|model) - P(damaging)")
p.save("damaging_miscalibration.png", width=12, height=8, unit='cm')

p = ggplot(rates, aes(x='wiki', y='dmg_miscalibration_pred',
                      group='group', color='group', fill='group'))
p = p + geom_bar(stat='identity', position='dodge')
p = p + ylab("E(P(damaging|model)) - P(damaging)")
p.save("damaging_miscalibration_pred.png", width=12, height=8, unit='cm')

p = ggplot(rates, aes(x='wiki', y='false_pos_dmg',
                      group='group', color='group', fill='group'))
p = p + geom_bar(stat='identity', position='dodge')
p = p + ylab("False positive rate (damaging)")
p.save("damaging_fpr.png", width=12, height=8, unit='cm')

p = ggplot(rates, aes(x='wiki', y='false_neg_dmg',
                      group='group', color='group', fill='group'))
p = p + geom_bar(stat='identity', position='dodge')
p = p + ylab("False negative rate (damaging)")
p.save("damaging_fnr.png", width=12, height=8, unit='cm')

p = ggplot(rates, aes(x='wiki', y='gf_miscalibration',
                      group='group', color='group', fill='group'))
p = p + geom_bar(stat='identity', position='dodge')
p = p + ylab("P(goodfaith|model) - P(goodfaith)")
p.save("goodfaith_miscalibration.png", width=12, height=8, unit='cm')

p = ggplot(rates, aes(x='wiki', y='gf_miscalibration_pred',
                      group='group', color='group', fill='group'))
p = p + geom_bar(stat='identity', position='dodge')
p = p + ylab("E(P(goodfaith|model)) - P(goodfaith)")
p.save("goodfaith_miscalibration_pred.png", width=12, height=8, unit='cm')

p = ggplot(rates, aes(x='wiki', y='true_pos_gf',
                      group='group', color='group', fill='group'))
p = p + geom_bar(stat='identity', position='dodge')
p = p + ylab("False positive rate (goodfaith)")
p.save("goodfaith_fpr.png", width=12, height=8, unit='cm')

p = ggplot(rates, aes(x='wiki', y='true_neg_gf',
                      group='group', color='group', fill='group'))
p = p + geom_bar(stat='identity', position='dodge')
p = p + ylab("False negative rate (goodfaith)")
p.save("goodfaith_fnr.png", width=12, height=8, unit='cm')
