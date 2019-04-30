#!/usr/bin/env python3
import pandas as pd
import glob
import dns.resolver
import pymysql as mysql

def get_mediawiki_section_dbname_mapping(mw_config_path, use_x1):
    db_mapping = {}
    if use_x1:
        dblist_section_paths = [mw_config_path.rstrip('/') + '/dblists/all.dblist']
    else:
        dblist_section_paths = glob.glob(mw_config_path.rstrip('/') + '/dblists/s[0-9]*.dblist')
    for dblist_section_path in dblist_section_paths:
        with open(dblist_section_path, 'r') as f:
            for db in f.readlines():
                db_mapping[db.strip()] = dblist_section_path.strip().rstrip('.dblist').split('/')[-1]
                
    return db_mapping


def get_dbstore_host_port(db_mapping, use_x1, dbname):
    if dbname == 'staging':
        shard = 'staging'
    elif use_x1:
        shard = 'x1'
    else:
        try:
            shard = db_mapping[dbname]
        except KeyError:
            raise RuntimeError("The database {} is not listed among the dblist files of the supported sections."
                               .format(dbname))
    answers = dns.resolver.query('_' + shard + '-analytics._tcp.eqiad.wmnet', 'SRV')
    host, port = str(answers[0].target), answers[0].port
    return (host,port)

def get_db_conn(dbname):
    mw_config_path = "/srv/mediawiki-config"
    use_x1 = False
    db_mapping = get_mediawiki_section_dbname_mapping(mw_config_path,use_x1)
    host,port = get_dbstore_host_port(db_mapping,use_x1,dbname='enwiki')

    conn = mysql.connect(host = host,
                         port = port,
                         database='enwiki',
                         read_default_file = "/etc/mysql/conf.d/analytics-research-client.cnf",
                         charset='utf8',
                         use_unicode=True,
                         autocommit=False)
    return conn

edit_data = pd.read_pickle("labeled_newcomers_anons.pickle")

wikis = set(edit_data.wiki)


base_query = "select pp_page, pp_value, pp_sortkey from page_props WHERE pp_page IN ({0}) AND pp_propname = 'wikibase_item'"

df_parts = []
for dbname in wikis:
    print(dbname)
    conn = get_db_conn(dbname)

    page_ids = set(edit_data.loc[edit_data.wiki == dbname].pageid)
    page_ids = ','.join([str(pid) for pid in page_ids])

    query = base_query.format(page_ids)
    df_part  = pd.read_sql_query(query,con=conn,index_col="pp_page")
    df_parts.append(df_part)

df = pd.concat(df_parts)

df.to_pickle("labeled_newcomers_anons_wikidata_ids.pickle")
