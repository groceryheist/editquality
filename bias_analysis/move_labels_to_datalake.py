from concurrent.futures import ThreadPoolExecutor
import itertools
import mwapi
from pyhive import hive

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
                yield out_row

def move_labels_to_datalake(label_files, wikis):
    conn = hive.Connection(host='an-coord1001.eqiad.wmnet', port=10000)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS nathante.ores_label_editors(ns string, pageid bigint, title string, revid bigint, parentid bigint, user string, userid bigint) PARTITIONED BY (wiki string)")

    cursor.execute("SET hive.exec.dynamic.partition.mode=nonstrict")
    query = """ INSERT INTO nathante.ores_label_editors PARTITION (wiki) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) """
    # writes a tsv
    with open("editor_revisions.tsv",'w') as label_metadata_temp1:
        out_schema = ['wiki','ns','pageid','title','revid','parentid','user','userid']
        print("collecting userids")
        label_metadata_temp1.write('\t'.join(out_schema))
        
        for label_file, context in zip(label_files,wikis):
            labels = load_labels(label_file)
            rows = get_editor_traits(labels,context,label_metadata_temp1)
            cursor.executemany(query,rows)

    conn.close()
# next step
