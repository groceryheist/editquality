import pandas as pd
import numpy as np
from qwikidata.sparql import return_sparql_query_results
from move_labels_to_datalake import grouper
import re

df = pd.read_pickle("labeled_newcomers_anons_wikidata_ids.pickle")
df.pp_value = df.pp_value.str.decode('utf-8')
df = df.reset_index()
endpoint = "https://query.wikidata.org/sparql"

# we want to get instance of, and sex or gender
base_query = """ SELECT ?s1 ?s2Label
            WHERE  {
                      {?s1 wdt:P31 wd:Q5}
                      {?s1 wdt:P21 ?s2}
            FILTER(?s1 IN (%s))
            SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
                   }
"""

entities = ["wd:{0}".format(e) for e in set(df.pp_value)]

N = int(np.ceil(len(entities) / 300))
batches = list(grouper(entities, 300))

found_entities = []
genders = []
entityre = re.compile("http://www.wikidata.org/entity/(.*)")
i = 0 
for batch in batches:
    i = i + 1
    print("batch {0} / {1}".format(i,N))
    query = base_query % ','.join(batch)

    response  = return_sparql_query_results(query)

    bindings = response['results']['bindings']
    found_entities.extend(entityre.findall(b['s1']['value'])[0] for b in bindings)
    genders.extend(b['s2Label']['value'] for b in bindings)
    

df2 = pd.DataFrame({"entity": found_entities, "gender":genders})
df = pd.merge(df, df2, left_on='pp_value', right_on='entity', how='left')
df = df.drop("pp_sortkey",1)
df.to_pickle("labeled_pages_genders.pickle")
# unpack the jsons

# join back to the original tabl
