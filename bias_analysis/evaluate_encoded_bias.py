#!/usr/bin/env python3
from plotnine import *
import pandas as pd
import itertools
from get_labels import load_labels, load_wikis, load_makefile, grep_labelfile
import json
import os
import numpy as np
import re

theme_set(theme_bw())

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

df['group'] = 'other'
df.loc[df.is_anon == True, 'group'] = 'anon'
df.loc[df.is_newcomer == True, 'group'] = 'newcomer'

df['wiki'] = df['wiki'].str.replace("wiki", "")

class ORESConfidenceLevel(object):
    def __init__(self, name, threshholds, inverse = False):
        self.threshholds = threshholds
        self.name = name
        self.pred_col_name = "pred_{0}".format(self.name)
        self.fp_col_name = "fp_{0}".format(self.name)
        self.fn_col_name = "fn_{0}".format(self.name)
        self.inverse = inverse


    def in_level(self, wiki, scores):
        interval = self.threshholds[wiki]
        if interval is None:
            return None

        if interval[0] > interval[1]:
            raise ValueError("interval is not ordered")
        return (scores > interval[0]) & (scores < interval[1])


    def gen_preds(self, df, model):
        wikis = set(df.wiki)
        true_col_name = "true_{0}".format(model)
        prob_col_name = "prob_{0}".format(model)
        for wiki in wikis:
            prob_col = df.loc[df.wiki == wiki, prob_col_name]
            true_col = df.loc[df.wiki == wiki, true_col_name]
            df.loc[df.wiki==wiki, self.pred_col_name] = self.in_level(wiki, prob_col)

        if not self.inverse:
            df[self.fp_col_name] = \
            ((df.loc[:,self.pred_col_name] == True) & (df.loc[:,true_col_name] == False)).astype("double")

            df[self.fn_col_name] = \
                ((df.loc[:,self.pred_col_name] == False) & (df.loc[:,true_col_name] == True)).astype("double")

        else: #self.inverse
            df[self.fp_col_name] = \
            ((df.loc[:,self.pred_col_name] == False) & (df.loc[:,true_col_name] == True)).astype("double")

            df[self.fn_col_name] = \
                ((df.loc[:,self.pred_col_name] == True) & (df.loc[:,true_col_name] == False)).astype("double")

            
        df.loc[df[self.pred_col_name].isna(),self.fp_col_name] = None
        df.loc[df[self.pred_col_name].isna(),self.fn_col_name] = None
        return df

dmg_levels = []
gf_levels = []

dmg_unlikely_threshholds = {'ar':(0,0.168), 'bs':(0,0.198), 'ca':(0,0.619), 'cs':(0,0.038),'data':(0,0.283),'en':(0,0.305), 'es':(0,0.208),'esbooks':(0,0.123), 'et':(0,0.231), 'fi':(0,0.00361), 'fr':(0,0.098), 'he':(0,0.006), 'hu':(0,0.068),'it':(0,0.151), 'ko':(0,0.283), 'lv':(0,0.148), 'nl':(0,0.573), 'pl':(0,0.038), 'pt':(0,0.253), 'ro':(0,0.246), 'ru':(0,0.484), 'sq':(0,0.087), 'sr':(0,0.157), 'sv':(0,0.518), 'tr':(0,0.148)}

dmg_levels.append(ORESConfidenceLevel("dmg_unlikely", dmg_unlikely_threshholds, inverse=True))

dmg_maybe_threshholds = {'ar':(0.153,1),'bs':(0.131,1), 'ca':(0.195,1), 'cs':(0.52,1),'data':None, 'en':(0.147,1), 'es':(0.527,1), 'esbooks':None, 'et':(0.151,1), 'fi':(0.01533,1), 'fr':(0.08,1), 'he':None, 'hu':(0.103,1), 'it':(0.15,1), 'ko':(0.153,1), 'lv':(0.281,1), 'nl':(0.378,1), 'pt':(0.229,1),'pl':None, 'ro':(0.296,1), 'ru':(0.365,1), 'sq':(0.121,1), 'sr':(0.058,1), 'sv':(0.172,1), 'tr':(0.194,1)}

dmg_levels.append(ORESConfidenceLevel("dmg_maybe", dmg_maybe_threshholds))

dmg_likely_threshholds = {'ar':(0.455,1),'bs':(0.346,1), 'ca':(0.779,1), 'cs':(0.623,1), 'data':(0.387,1),'en':(0.626,1), 'es':(0.85,1), 'esbooks':(0.697,1), 'et':(0.641,1), 'fi':(0.25513,1), 'fr':(0.774,1), 'he':(0.181,1), 'hu':(0.805,1), 'it':(0.67,1), 'ko':(0.699,1), 'lv':(0.801,1), 'nl':(0.795,1), 'pl':(0.941,1), 'pt':(0.819,1),'ro':(0.857,1), 'ru':(0.785,1), 'sq':(0.801,1), 'sr':(0.638,1), 'sv':(0.779,1), 'tr':(0.704,1)}

dmg_levels.append(ORESConfidenceLevel("dmg_likely", dmg_likely_threshholds))

dmg_very_likely_threshholds = {'ar':None,'bs':(0.549,1), 'ca':(0.924,1), 'cs':(0.908,1), 'data':(0.925,1), 'en':(0.927,1),'es':(0.961,1), 'esbooks':(0.947,1), 'et':(0.937,1), 'fi':(0.62696,1), 'fr':(0.859,1), 'he':None, 'hu':(0.87,1), 'it':(0.825,1), 'ko':(0.851,1), 'lv':(0.892,1), 'nl':(0.931,1), 'pl':(0.941,1), 'pt':(0.949,1), 'ro':(0.915,1), 'ru':(0.916,1), 'sq':(0.901,1), 'sr':(0.873,1), 'sv':(0.948,1), 'tr':(0.88,1)} 

dmg_levels.append(ORESConfidenceLevel("dmg_very_likely", dmg_very_likely_threshholds))

gf_very_likely_threshholds = {'ar':(0.999,1), 'bs':(0.999,1), 'ca':(0.999,1), 'cs':(0.747,1), 'data':(0.969,1), 'en':(0.787,1),'es':None, 'esbooks':(1,1), 'et':(0.682,1), 'fi':None, 'fr':(0.777,1), 'he':None, 'hu':(0.957,1), 'it':(0.87,1), 'ko':(0.617,1), 'lv':(0.997,1), 'nl':(0.596,1), 'pl':(0.912,1), 'pt':(0.866,1), 'ro':(0.895,1), 'ru':(0.762,1), 'sq':(0.919,1), 'sr':None, 'sv':(0.982,1), 'tr':(0.86,1)}

gf_levels.append(ORESConfidenceLevel("gf_very_likely", gf_very_likely_threshholds, inverse=False))

gf_likely_threshholds = {'ar':(0,1),'bs':(0,0.999),'ca':(0,0.999), 'cs':(0,0.95),'data':None,'en':(0,0.933), 'es':None, 'esbooks':None, 'et':(0,0.898), 'fi':(0,1), 'fr':(0,0.962), 'he':None, 'hu':None, 'it':(0,0.865), 'ko':(0,0.606),'lv':(0,0.999), 'nl':(0,0.691), 'pt':(0,0.782), 'pl':None, 'ro':(0,0.793), 'ru':(0,0.769), 'sq':(0,0.942), 'sr':None, 'sv':(0,0.89), 'tr':(0,0.84)}

gf_levels.append(ORESConfidenceLevel("gf_likely", gf_likely_threshholds, inverse=True))

gf_unlikely_threshholds = {'ar':None,'bs':(0,0.786), 'ca':(0,0.926), 'cs':(0,0.44),'data':(0,0.997),'en':(0,0.357), 'es':None, 'esbooks':(0,0.997),'et':(0,0.572), 'fi':None, 'fr':(0,0.281), 'he':(0,0.941), 'hu':(0,0.932), 'it':(0,0.343), 'ko':(0,0.216), 'lv':(0,0.901), 'nl':(0,0.319), 'pt':(0,0.206),'pl':None, 'ro':(0,0.154), 'ru':(0,0.244), 'sq':(0,0.265), 'sr':None, 'sv':(0,0.599), 'tr':(0,0.339)}

gf_levels.append(ORESConfidenceLevel("gf_unlikely", gf_unlikely_threshholds,inverse=True))

gf_very_unlikely_threshholds = {'ar':None, 'bs':None, 'ca':(0,0.031), 'cs':(0,0.111), 'data':None, 'en':(0,0.071), 'es':(0,0.451), 'esbooks':(0,0.001), 'et':(0,0.186), 'fi':None, 'fr':(0,0.106), 'he':(0,0.006), 'hu':(0,0.181),'it':(0,0.151), 'ko':None, 'lv':(0,0.002), 'nl':(0,0.11), 'pl':(0,0.244), 'pt':(0,0.058), 'ro':(0,0.074), 'ru':None, 'sq':(0,0.057), 'sr':None, 'sv':(0,0.237), 'tr':(0,0.162)}

gf_levels.append(ORESConfidenceLevel("gf_very_unlikely", gf_very_unlikely_threshholds, inverse=True))


for confidenceLevel in dmg_levels:
    df = confidenceLevel.gen_preds(df, "damaging")

for confidenceLevel in gf_levels:
    df = confidenceLevel.gen_preds(df, "goodfaith")


df['true_damaging'] = df['true_damaging'].astype("double")
df['true_goodfaith'] = df['true_goodfaith'].astype("double")
gb = df.groupby(["wiki", "group"])
rates = gb.agg(['mean','std'])
v = list(rates.columns.levels[0][1:].values)
rates['count'] =  gb.wiki.count()
rates.columns = rates.columns.to_flat_index()
rates.columns = ['_'.join([s for s in t if s != '']) for t in rates.columns]

rates['dmg_miscalibration_mean'] = (rates['prob_damaging_mean'] - rates['true_damaging_mean'])
rates['dmg_miscalibration_std'] = np.sqrt(rates['prob_damaging_std'].pow(2) +  rates['true_damaging_std'].pow(2))
rates['gf_miscalibration_mean'] = rates['prob_goodfaith_mean'] - rates['true_goodfaith_mean']
rates['gf_miscalibration_std'] = np.sqrt((rates['prob_goodfaith_std']).pow(2) +  rates['true_goodfaith_std'].pow(2))

v.append("dmg_miscalibration")
v.append("gf_miscalibration")

d = np.sqrt(rates.loc[:,"count"])
for var in v:
    m = rates.loc[:,"{0}_mean".format(var)]
    s = rates.loc[:,"{0}_std".format(var)]
    rates["{0}_upper".format(var)] = m + 1.96*s / d
    rates["{0}_lower".format(var)] = m - 1.96*s / d

rates = rates.reset_index()

# re_damaging_uppers = r".*_dmg_.*_upper"
# re_damaging_lowers = r"*_dmg_.*_lowers"
# re_damaging_means = r".*_dmg_.*_mean"

# re_goodfaith_uppers = r".*_gf_.*_upper"434
# re_goodfaith_lowers = r".*_gf_.*_lowers"
# re_goodfaith_means = r".*_gf_.*_mean"

def build_plot_dataset(rates, prefix):

    rates_1 = rates.melt(id_vars = ['wiki','group'],value_vars = [col for col in list(rates.columns) if (re.match(r"{0}_.*_upper".format(prefix), col)) ], value_name ='upper')

    rates_1['variable'] = rates_1['variable'].str.replace("_upper","")

    rates_2 = rates.melt(id_vars = ['wiki','group'],value_vars = [col for col in list(rates.columns) if (re.match(r"{0}_.*_lower".format(prefix), col)) ], value_name = 'lower')

    rates_2['variable'] = rates_2['variable'].str.replace("_lower","")

    rates_3 = rates.melt(id_vars = ['wiki','group'],value_vars = [col for col in list(rates.columns) if (re.match(r"{0}_.*_mean".format(prefix), col)) ], value_name='mean')

    rates_3['variable'] = rates_3['variable'].str.replace("_mean","")

    plot_rates = pd.merge(rates_1, rates_2)
    plot_rates = pd.merge(plot_rates, rates_3)
    plot_rates['variable'] = plot_rates['variable'].astype('category')

    return plot_rates

fp_rates_damaging = build_plot_dataset(rates, 'fp_dmg')

fp_rates_damaging.variable.cat.reorder_categories(['fp_dmg_unlikely', 'fp_dmg_maybe','fp_dmg_likely','fp_dmg_very_likely'],ordered=True,inplace=True)

fp_rates_damaging.variable.cat.rename_categories(['Very likely good', 'May have problems','Likely have problems','Very likely have problems'],inplace=True)

p = ggplot(fp_rates_damaging, aes(x='wiki', y='mean',ymin= 'lower', ymax = 'upper', group='group',color='group')) + geom_pointrange(position=position_dodge(width=0.5)) + facet_wrap(facets='variable', ncol=2, nrow=2, scales='free_y') 

p = p + ylab("False positive rate (Damage predicted, but actually good)")
p = p + ggtitle("Bias of damaging model against newcomers and anons")
p = p + theme(legend_position='right')
p = p + theme(legend_title=element_blank())
p.save("Damaging_fpr.png",width=18, height=8,units='in')

fn_rates_damaging = build_plot_dataset(rates, 'fn_dmg')

fn_rates_damaging.variable.cat.reorder_categories(['fn_dmg_unlikely', 'fn_dmg_maybe','fn_dmg_likely','fn_dmg_very_likely'],ordered=True,inplace=True)

fn_rates_damaging.variable.cat.rename_categories(['Very likely good', 'May have problems','Likely have problems','Very likely have problems'],inplace=True)

p = ggplot(fn_rates_damaging, aes(x='wiki', y='mean',ymin= 'lower', ymax = 'upper', group='group',color='group')) + geom_pointrange(position=position_dodge(width=0.5)) + facet_wrap(facets='variable', ncol=2, nrow=2, scales='free_y') 

p = p + ylab("False negative rate (Damage not predicted, but actually damaging)")
p = p + ggtitle("Bias of damaging model against newcomers and anons")
p = p + theme(legend_position='right')
p = p + theme(legend_title=element_blank())
p.save("Damaging_fnr.png",width=18, height=8,units='in')

fp_rates_goodfaith = build_plot_dataset(rates, 'fp_gf')

fp_rates_goodfaith.variable.cat.reorder_categories(['fp_gf_very_likely', 'fp_gf_likely','fp_gf_unlikely','fp_gf_very_unlikely'],ordered=True,inplace=True)

fp_rates_goodfaith.variable.cat.rename_categories(['Very likely good faith', 'May be bad faith','Likely bad faith','Very likely bad faith'],inplace=True)

p = ggplot(fp_rates_goodfaith, aes(x='wiki', y='mean',ymin= 'lower', ymax = 'upper', group='group',color='group')) + geom_pointrange(position=position_dodge(width=0.5)) + facet_wrap(facets='variable', ncol=2, nrow=2, scales='free_y') 

p = p + ylab("False positive rate (Goodfaith predicted, but actually badfaith)")
p = p + ggtitle("Bias of goodfaith model against newcomers and anons")
p = p + theme(legend_position='right')
p = p + theme(legend_title=element_blank())
p.save("Goodfaith_fpr.png",width=18, height=8,units='in')


fn_rates_goodfaith = build_plot_dataset(rates, 'fn_gf')

fn_rates_goodfaith.variable.cat.reorder_categories(['fn_gf_very_likely', 'fn_gf_likely','fn_gf_unlikely','fn_gf_very_unlikely'],ordered=True,inplace=True)

fn_rates_goodfaith.variable.cat.rename_categories(['Very likely good faith', 'May be bad faith','Likely bad faith','Very likely bad faith'],inplace=True)

p = ggplot(fn_rates_goodfaith, aes(x='wiki', y='mean',ymin= 'lower', ymax = 'upper', group='group',color='group')) + geom_pointrange(position=position_dodge(width=0.5)) + facet_wrap(facets='variable', ncol=2, nrow=2, scales='free_y') 

p = p + ylab("False negative rate (Badfaith predicted, but actually goodfaith)")
p = p + ggtitle("Bias of goodfaith model against newcomers and anons")
p = p + theme(legend_position='right')
p = p + theme(legend_title=element_blank())
p.save("Goodfaith_fnr.png",width=18, height=8,units='in')

p = ggplot(rates, aes(x='wiki', y='dmg_miscalibration_mean',ymax='dmg_miscalibration_upper',ymin='dmg_miscalibration_lower',
                      group='group', color='group', fill='group'))
p = p + geom_pointrange(position = position_dodge(width=0.5))
p = p + ylab("P_model(damaging) - P(damaging)")
p = p + ggtitle("Calibration of ORES damaging model")
p = p + theme(legend_title = element_blank())
p.save("damaging_miscalibration.png", width=16, height=8, unit='cm')

p = ggplot(rates, aes(x='wiki', y='gf_miscalibration_mean',ymax='gf_miscalibration_upper',ymin='gf_miscalibration_lower',
                      group='group', color='group', fill='group'))
p = p + geom_pointrange(position = position_dodge(width=0.5))
p = p + ylab("P_model(goodfaith) - P(goodfaith)")
p = p + ggtitle("Calibration of ORES goodfaith model")
p = p + theme(legend_title = element_blank())
p.save("goodfaith_miscalibration.png", width=12, height=8, unit='cm')

# p = ggplot(rates, aes(x='wiki', y='false_pos_dmg_mean', ymax='false_pos_dmg_upper',ymin='false_pos_dmg_lower',
#                       group='group', color='group', fill='group'))
# p = p + geom_pointrange()
# p = p + ylab("False positive rate (damaging)")
# p.save("damaging_fpr.png", width=12, height=8, unit='cm')

# p = ggplot(rates, aes(x='wiki', y='false_neg_dmg_mean',ymax='false_neg_dmg_upper',ymin='false_neg_dmg_lower',
#                       group='group', color='group', fill='group'))
# p = p + geom_pointrange()
# p = p + ylab("False negative rate (damaging)")
# p.save("damaging_fnr.png", width=12, height=8, unit='cm')

# p = ggplot(rates, aes(x='wiki', y='false_pos_gf_mean',ymax='false_pos_gf_upper',ymin='false_pos_gf_lower',
#                       group='group', color='group', fill='group'))
# p = p + geom_pointrange()
# p = p + ylab("False positive rate (goodfaith)")
# p.save("goodfaith_fpr.png", width=12, height=8, unit='cm')

# p = ggplot(rates, aes(x='wiki', y='false_neg_gf_mean',ymax='false_neg_gf_upper',ymin='false_neg_gf_lower',
#                       group='group', color='group', fill='group'))
# p = p + geom_pointrange()
# p = p + ylab("False negative rate (goodfaith)")
# p.save("goodfaith_fnr.png", width=12, height=8, unit='cm')


# for confidenceLevel in dmg_levels:
#     confidenceLevel.make_plots(rates, "damaging")

# for confidenceLevel in gf_levels:
#     confidenceLevel.make_plots(rates, "goodfaith")


# df['true_dmg'] = df['pred_damaging'] == df['true_damaging']
# df['false_pos_dmg'] = (df['true_dmg'] == False) & (df['pred_damaging'])
# df['false_neg_dmg'] = df['true_dmg'] & (df['pred_damaging'] == False)

# df['true_gf'] = df['pred_goodfaith'] == df['true_goodfaith']
# df['false_pos_gf'] = (df['true_gf'] == False) & df['pred_goodfaith']
# df['false_neg_gf'] = (df['true_gf'] == True) & \
#     (df['pred_goodfaith'] == False)

# df['pred_damaging'] = df['pred_damaging'].astype("double")
# df['pred_goodfaith'] = df['pred_goodfaith'].astype("double")
