#!/usr/bin/env python3

import pyspark.sql.functions as f
from pyspark import SparkContext, SparkConf
from pyspark.sql import SparkSession

conf = SparkConf()
conf = conf.set("spark.sql.crossJoin.enabled",'true')
sc = SparkContext(conf= conf)
spark = SparkSession(sc)
import pyspark.sql.functions as f




reader = spark.read
wikidata_parquet = "/user/joal/wmf/data/wmf/mediawiki/wikidata_parquet/20190204"
mapping_parquet = "/user/joal/wmf/data/wmf/wikidata/item_page_link/20190204"

df = reader.parquet("/user/nathante/ores_bias/nathante.ores_label_editors")

mapping = reader.parquet(mapping_parquet)

# lookup wikidata ids
df2 = df.join(mapping, on=[df.pageid == mapping.page_id, df.ns == mapping.page_namespace, df.wiki == mapping.wiki_db])

df2 = df2.select(["ns","pageid","revid","title","user","userid","wiki","item_id","title_namespace_localized"])

# now lookup wikidata fields

wikidata = reader.parquet(wikidata_parquet)

wikidata

wikidata_entities = wikidata.join(df2, on=[df2.item_id == wikidata.id])

wikidata_entities = wikidata_entities.cache()

claims = wikidata_entities.select(["id","ns","wiki","pageid","revid",f.explode("claims").alias("claim")])

snaks = claims.select(["id","ns","wiki","pageid","revid",f.col("claim").mainSnak.alias("mainSnak")])

from pyspark.sql.types import *

dataValue_schema = StructType([StructField("entity-type",StringType()), StructField("numeric-id",IntegerType()), StructField("id", StringType())])

values = snaks.select(["id","ns","wiki","pageid","revid",f.col("mainSnak").property.alias("property"),f.col("mainSnak").dataType.alias("dataType"), f.from_json(f.col("mainSnak").dataValue.value,schema=dataValue_schema).alias("dataValue")]).filter(f.col("property").isin(["P31","P21"])) 

values = values.select([f.col("id").alias("entityid"),"property",f.col("dataValue").id.alias("valueid"),"ns","wiki","pageid","revid"])

values = values.join(wikidata,on=[values.valueid == wikidata.id])

values = values.select(['entityid','property',f.col("id").alias('valueid'),f.col("labels")['en'].alias("valuelabel")],"wiki","ns","pageid","revid")

values = values.filter( (f.col("valueid")=="Q5") | (f.col("property")=="P21"))

pddf = values.toPandas()

pddf.to_pickle("page_wikidata_properties.pickle")

