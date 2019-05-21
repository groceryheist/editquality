
install.packages("sandwich")

library(MASS)
library(aod)
library(sandwich)
library(sjPlot)
library(lmtest)

library(lmtest)

source("ob_util.R")

df <- load_ts_ds()

set.seed(123)

# gotta do a regex replace to fix some of the names
names(df)[42:71] <- sapply(names(df)[42:71], function(n) paste0("ns",n))

df[,wiki_db := factor(wiki_db)]

cutoffs <- df[treated==T,cutoff]
get_rand_cutoff <- function(wiki){
    return(sample(cutoffs,1))
}

df[treated == F, cutoff := get_rand_cutoff(wiki_db),by=.(wiki_db)]

df[treated == F, weeks_from_cutoff := round((week - cutoff)/dweeks(1))]

# there's a problem with n_pages_baseline

df[is.na(view_count),view_count := 0]
df[is.na(patroller_N_reverts),patroller_N_reverts := 0]
df[is.na(admin_N_reverts),admin_N_reverts := 0]
df[is.na(bot_N_reverts),bot_N_reverts := 0]
df[is.na(other_N_reverts),other_N_reverts := 0]
df[is.na(anonymous_n_reverted),anonymous_n_reverted := 0]
df[is.na(newcomer_n_reverted),newcomer_n_reverted := 0]
df[is.na(established_n_reverted),established_n_reverted := 0]
df[is.na(ns4_anon_N_edits),ns4_anon_N_edits := 0]
df[is.na(ns4_newcomer_N_edits),ns4_newcomer_N_edits := 0]
df[is.na(ns4_non_anon_newcomer_N_edits),ns4_non_anon_newcomer_N_edits := 0]
df[is.na(ns0_anon_N_edits),ns0_anon_N_edits := 0]
df[is.na(ns0_newcomer_N_edits),ns0_newcomer_N_edits := 0]
df[is.na(ns0_non_anon_newcomer_N_edits),ns0_non_anon_newcomer_N_edits := 0]
df[is.na(n_pages_baseline_ns_0),n_pages_baseline_ns_0 := 0]
df[is.na(n_pages_baseline_ns_4),n_pages_baseline_ns_4 := 0]
df[is.na(user_week_revert_cv),user_week_revert_cv := 0]
df[is.na(geom_mean_ttr),geom_mean_ttr := 0]

wiki_stats = df[(weeks_from_cutoff > -52) & (week < cutoff),
                .(treated = any(treated,na.rm=T),
#                  reverts_per_week = mean(n_reverts,na.rm=T),
                  user_revert_cv = mean(user_week_revert_cv,na.rm=T),
#                  edits = mean(total_edits,na.rm=T),
                  active_editors = mean(active_editors,na.rm=T),
                  ttr = mean(geom_mean_ttr,na.rm=T),
#                         admin_ttr = mean(admin_geom_mean_ttr,na.rm=T), 
#                         bot_ttr = mean(bot_geom_mean_ttr,na.rm=T), 
                  admin_reverts = mean(admin_N_reverts,na.rm=T), 
                  bot_reverts = mean(bot_N_reverts,na.rm=T), #
#                         patroller_ttr = mean(patroller_mean_ttr,na.rm=T),
                  patroller_reverts = mean(patroller_N_reverts,na.rm=T),
#                         other_ttr = mean(other_mean_ttr,na.rm=T), 
                  other_reverts = mean(other_N_reverts,na.rm=T),
                  newcomer_reverted = mean(newcomer_n_reverted,na.rm=T),
 #                        newcomer_ttr = mean(newcomer_mean_ttr,na.rm=T),
                  anon_reverted = mean(anonymous_n_reverted,na.rm=T),
 #                        anon_ttr = mean(anonymous_mean_ttr,na.rm=T), 
 #                 established_reverted = mean(established_n_reverted,na.rm=T),
 #                        established_ttr = mean(established_mean_ttr,na.rm=T),
                  ns0_anon_edits = mean(ns0_anon_N_edits,na.rm=T),
      #                   ns0_anon_editors = mean(ns0_anon_N_editors,na.rm=T),
                  ns0_newcomer_edits = mean(ns0_newcomer_N_edits,na.rm=T),
     #                    ns0_newcomer_editors = mean(ns0_newcomer_N_editors,na.rm=T),
                  ns0_established_edits = mean(ns0_non_anon_newcomer_N_edits,na.rm=T),
    #                     ns0_established_editors = mean(ns0_non_anon_newcomer_N_editors,na.rm=T),
    #                     ns1_anon_edits = mean(ns1_anon_N_edits,na.rm=T),
   #                      ns1_anon_editors = mean(ns1_anon_N_editors,na.rm=T),
   #                      ns1_newcomer_edits = mean(ns1_newcomer_N_edits,na.rm=T),
  #                       ns1_newcomer_editors = mean(ns1_newcomer_N_editors,na.rm=T),
  #                       ns1_established_edits = mean(ns1_non_anon_newcomer_N_edits,na.rm=T),
 #                        ns1_established_editors = mean(ns1_non_anon_newcomer_N_editors,na.rm=T),
 #                       ns2_anon_edits = mean(ns2_anon_N_edits,na.rm=T),
#                         ns2_anon_editors = mean(ns2_anon_N_editors,na.rm=T),
 #                        ns2_newcomer_edits = mean(ns2_newcomer_N_edits,na.rm=T),
#                         ns2_newcomer_editors = mean(ns2_newcomer_N_editors,na.rm=T),
 #                        ns2_established_edits = mean(ns2_non_anon_newcomer_N_edits,na.rm=T),
#                         ns2_established_editors = mean(ns2_non_anon_newcomer_N_editors,na.rm=T),
 #                        ns3_anon_edits = mean(ns3_anon_N_edits,na.rm=T),
#                         ns3_anon_editors = mean(ns3_anon_N_editors,na.rm=T),
#                         ns3_newcomer_edits = mean(ns3_newcomer_N_edits,na.rm=T),
#                         ns3_newcomer_editors = mean(ns3_newcomer_N_editors,na.rm=T),
#                         ns3_established_edits = mean(ns3_non_anon_newcomer_N_edits,na.rm=T),
#                         ns3_established_editors = mean(ns3_non_anon_newcomer_N_editors,na.rm=T),
                  ns4_edits = mean(ns4_anon_N_edits + ns4_newcomer_N_edits + ns4_non_anon_newcomer_N_edits, na.rm=T),
#                  ns4_anon_edits = mean(ns4_anon_N_edits,na.rm=T),
#                         ns4_anon_editors = mean(ns4_anon_N_editors,na.rm=T),
#                  ns4_nelwcomer_edits = mean(ns4_newcomer_N_edits,na.rm=T),
#                         ns4_newcomer_editors = mean(ns4_newcomer_N_editors,na.rm=T),
#                  ns4_established_edits = mean(ns4_non_anon_newcomer_N_edits,na.rm=T),
#                         ns4_established_editors = mean(ns4_non_anon_newcomer_N_editors,na.rm=T),
                  view_count = mean(view_count,na.rm=T)
#                         n_pages_created_ns_0 =  mean(n_pages_created_ns_0,na.rm=T),
#                         n_pages_created_ns_1 =  mean(n_pages_created_ns_1,na.rm=T),
#                         n_pages_created_ns_2 = mean(n_pages_created_ns_2,na.rm=T),
#                         n_pages_created_ns_3 = mean(n_pages_created_ns_3,na.rm=T),
#                         n_pages_created_ns_4 = mean(n_pages_created_ns_4,na.rm=T),
#                  n_pages_baseline_ns_0 = mean(n_pages_baseline_ns_0,na.rm=T),
#                         n_pages_baseline_ns_1 = mean(n_pages_baseline_ns_1,na.rm=T),
#                         n_pages_baseline_ns_2 = mean(n_pages_baseline_ns_2,na.rm=T),
#                         n_pages_baseline_ns_3 = mean(n_pages_baseline_ns_3,na.rm=T),
#                  n_pages_baseline_ns_4 = mean(n_pages_baseline_ns_4,na.rm=T)),
                  ),
                by=.(wiki_db)]


# for (name in names(wiki_stats)){
#     if(is.numeric(wiki_stats[[name]])){
#         wiki_stats[[name]] <- scale(wiki_stats[[name]])
#     }
# }

wiki_stats

treated_model = glm(data =wiki_stats, formula=treated ~ . - wiki_db, family=binomial(link='logit'),na.action = na.fail)

summary(treated_model)

wiki_stats[,treated_odds_pred := exp(predict(treated_model,wiki_stats))]
wiki_stats[,treated_probs_pred := treated_odds_pred / (1+treated_odds_pred)]
wiki_stats[treated == T,ip_weight := 1/treated_probs_pred]
wiki_stats[treated == F,ip_weight := 1/(1-treated_probs_pred)]

wiki_stats[treated_probs_pred > 0.10 | treated,
           .(mean(treated_probs_pred),.N),by=.(treated)]

# add the IP-weights to the df
df <- merge(df,wiki_stats,by=c("wiki_db"),how='left outer',suffixes=c('','.y'))

# let's check if excluding the wikis with the fewest reverts changes things
# df = df[N_reverts >= median(N_reverts)]

#for this test we'll use random cutoffs for each wiki 

df <- df[order(wiki_db,week)]

df[,":="(geom_mean_ttr_l1 = shift(geom_mean_ttr,type = 'lag',n=1),
        geom_mean_ttr_l2 = shift(geom_mean_ttr,type = 'lag',n=2),
        geom_mean_ttr_l3 = shift(geom_mean_ttr,type = 'lag',n=3),
        geom_mean_ttr_l4 = shift(geom_mean_ttr,type = 'lag',n=4))]

df[,":="(geom_mean_ttr_l1pl2 = geom_mean_ttr_l1 + geom_mean_ttr_l2)]

df[,":="(week_factor = factor(week))]

mod_treatment_test <- glm(df[(weeks_from_cutoff ==0)] ,formula = "treated ~ geom_mean_ttr_l1 + geom_mean_ttr_l1pl2", family=binomial(link='logit'))

summary(mod_treatment_test)

names(df[(weeks_from_cutoff==0)])

df <- df[,geom_mean_ttr_demeaned := geom_mean_ttr - mean(.SD[['geom_mean_ttr']]), by=.(wiki_db)]
df <- df[,weeks_from_cutoff_sq := weeks_from_cutoff^2, by=.(wiki_db)]
df <- df[,N_reverts_demeaned := N_revert - mean(.SD[["N_revert"]]), by=.(wiki_db)]
df <- df[,ineq_demeaned := user_week_revert_cv - mean(user_week_revert_cv), by=.(wiki_db)]
df <- df[,hhi_demeaned := revert_hhi - mean(revert_hhi), by=.(wiki_db)]
df <- df[,treated_with_ores := treated & has_ores]

names(df)

# we have clustered errors
# H1 geom_mean_ttr
# DID only 
mod1_did <- lm(df,formula="geom_mean_ttr ~ 1 + treated + week_factor + treated_with_ores")

vcov_did <- sandwich::vcovCL(mod1_did,df$wiki_db)


coeftest(mod1_did,vcov_did)

#with IP weights
mod1_ip <- lm(df,formula=as.formula("geom_mean_ttr ~ 1 + treated + week_factor + treated_with_ores"), weights = df$ip_weight)

vcov_ip <- sandwich::vcovCL(mod1_ip,df$wiki_db)

coeftest(mod1_ip,vcov_ip)

#doubly robust 
mod1_dr <- lm(df, formula=as.formula("geom_mean_ttr ~ 1 + treated + week_factor + treated_with_ores + user_revert_cv + active_editors + admin_reverts + bot_reverts + patroller_reverts + other_reverts + newcomer_reverted + anon_reverted + ns0_anon_edits + ns0_newcomer_edits + ns0_established_edits + ns4_edits + view_count"), weights=df$ip_weight)

vcov_dr <- sandwich::vcovCL(mod1_dr,df$wiki_db)

coeftest(mod1_dr,vcov_dr)

summary(mod1_ip)

summary(mod1_dr)

mod1 <- lm(df,formula="geom_mean_ttr_demeaned ~ 1 + treated + week_factor + treated_with_ores")

summary(mod1)

df <- df[,mod1_pred := predict(mod1,df)]

qplot(log1p(df$N_revert),bins=80)

df2 <- df

library(aod)

# H1a number of reverts
# DID only
mod2_did <- negbin(data=df, formula="N_revert ~ 1 + treated + week_factor + treated_with_ores",random=~ 1)
saveRDS(object=mod2_did,file = "ores_bias_data/mod2_did.RDS")

mod2_ip <- negbin(data=df, formula="N_revert ~ 1 + treated + week_factor + treated_with_ores", random=~1,weights=df2$ip_weight)
saveRDS(object=mod2_ip,file = "ores_bias_data/mod2_ip.RDS")

# doubly robust
mod2_dr <- negbin(data=df, formula="N_revert ~ 1 + treated + week_factor + treated_with_ores + user_week_revert_cv + geom_mean_ttr + active_editors + ns0_anon_edits + ns0_newcomer_edits + ns0_established_edits + ns4_edits + view_count + geom_mean_ttr", random=~1,weights = df2$ip_weight)
saveRDS(object=mod2_dr,file = "ores_bias_data/mod2_dr.RDS")

summary(mod2_did)

summary(mod2_ip)

summary(mod2_dr)

summary(mod2a)

mod2 <- lm(df, formula="N_reverts_demeaned ~ 1 + treated + week_factor + treated_with_ores")

summary(mod2)

# H2 inequality

names(df)

# there's still a problem with the inequality measures

qplot(log(df$revert_hhi))

df[user_week_revert_cv == 0,.(wiki_db,any(treated), mean(N_reverts)),by='wiki_db']

# DID onlyh
mod3_did <- lm(df[user_week_revert_cv != 0], formula="log(user_week_revert_cv) ~ 1 + treated + week_factor + treated_with_ores")

vcov_did <- sandwich::vcovCL(mod3_did,df[user_week_revert_cv!=0]$wiki_db)

coeftest(mod3_did,vcov_did)

# IP weights
df2 <- df[user_week_revert_cv != 0]

mod3_ip <- lm(df[user_week_revert_cv != 0], formula="log(user_week_revert_cv) ~ 1 + treated + week_factor + treated_with_ores", weights = df2$ip_weight)

vcov_did <- sandwich::vcovCL(mod3_ip,df[user_week_revert_cv!=0]$wiki_db)

coeftest(mod3_ip,vcov_did)

mod3_dr <- lm(df[user_week_revert_cv != 0], formula="log(user_week_revert_cv) ~ 1 + treated + week_factor + treated_with_ores + geom_mean_ttr + active_editors + admin_reverts + geom_mean_ttr + newcomer_reverted + anon_reverted + ns0_anon_edits + ns0_newcomer_edits + ns0_established_edits + ns4_edits + view_count + admin_reverts + bot_reverts + patroller_reverts + other_reverts", weights = df2$ip_weight)

vcov_dr <- sandwich::vcovCL(mod3_dr,df[user_week_revert_cv!=0]$wiki_db)

coeftest(mod3_dr,vcov_dr)


qplot(log(1+df$user_week_revert_cv))

summary(mod3_ip)

summary(mod2_dr)

mod3 <- lm(df, formula="ineq_demeaned ~ 1 + treated + week_factor + treated_with_ores")

summary(mod3)

df[,mod3.pred := predict(mod3,df)]

vcov_did <- sandwich::vcovCL(mod3_did,df[user_week_revert_cv!=0]$wiki_db)

coeftest(mod3_did,vcov_did)

ggplot(df,aes(x=weeks_from_cutoff)) + geom_point(aes(y=ineq_demeaned,color='data')) + geom_point(data=df,aes(y=mod3.pred,color='predicted')) + facet_wrap(.~never_treated) + geom_vline(data=df,xintercept=0)



mod4 <- lm(df, formula="hhi_demeaned ~ has_ores never_treated*week_factor")

summary(mod4)


