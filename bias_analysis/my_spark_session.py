#!usr/bin/env python3
from pyspark import SparkConf
from pyspark.sql import SparkSession
import pyspark
import findspark
import os
os.environ['SPARK_HOME'] = "/usr/lib/spark2"
findspark.init()
conf = SparkConf().setAppName("test_spark_connect").setMaster("yarn")
conf.setAll([
    ("spark.driver.memory", "4g"),
    ("appName", "test_spark_connect"),
    ("sparkHome", "/usr/lib/spark2"),
    ("spark.driver.cores", '1'),
    ("spark.executor.memory", '8g'),
    ("spark.executor.memoryOverhead", "2g"),
    ("spark.shuffle.service.enabled", True),
    ("spark.dynamicAllocation.enabled", True)])

sc = pyspark.SparkContext(conf=conf)
spark = SparkSession(sc)
