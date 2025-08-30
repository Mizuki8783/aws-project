import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

from awsglue.dynamicframe import DynamicFrame

## @params: [TempDir, JOB_NAME]
args = getResolvedOptions(sys.argv, ['TempDir', 'JOB_NAME'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

## @type: DataSource
## @args: [database = "aws-project", table_name = "aws_bulkimport", transformation_ctx = "datasource0"]
## @return: datasource0
## @inputs: []
datasource0 = glueContext.create_dynamic_frame.from_catalog(
    database="aws-project",
    table_name="s3_bulkimport",
    transformation_ctx="datasource0"
)

## @type: ApplyMapping
## @args: [mapping = [("invoiceno", "string", "invoiceno", "int"),
##                   ("stockcode", "string", "stockcode", "string"),
##                   ("description", "string", "description", "string"),
##                   ("quantity", "long", "quantity", "long")]]
## @return: applymapping1
## @inputs: [frame = datasource0]
applymapping1 = ApplyMapping.apply(
    frame=datasource0,
    mappings=[
        ("invoiceno", "string", "invoiceno", "string"),
        ("stockcode", "string", "stockcode", "string"),
        ("description", "string", "description", "string"),
        ("quantity", "int", "quantity", "int"),
        ("invoicedate", "string", "invoicedate", "string"),
        ("unitprice", "double", "unitprice", "double"),
        ("customerid", "string", "customerid", "string"),
        ("country", "string", "country", "string"),

    ]
)

## @type: SelectFields
## @args: [paths = ["country", "quantity", "customerid", "description",
##                  "invoiceno", "unitprice", "invoicedate", "stockcode"]]
## @return: selectfields2
## @inputs: [frame = applymapping1]
selectfields2 = SelectFields.apply(
    frame=applymapping1,
    paths=[
        "country",
        "quantity",
        "customerid",
        "description",
        "invoiceno",
        "unitprice",
        "invoicedate",
        "stockcode"
        ]
)

## @type: ResolveChoice
## @args: [choice = "MATCH_CATALOG", database = "aws-project",
##         table_name = "transactionsredshift_public_bulkimport"]
## @return: resolvechoice3
## @inputs: [frame = selectfields2]
resolvechoice3 = ResolveChoice.apply(
    frame=selectfields2,
    choice="MATCH_CATALOG",
    database="aws-project",
    table_name="dev_public_bulkimport",
    transformation_ctx="resolvechoice3"
)

## @type: ResolveChoice
## @args: [choice = "make_cols", transformation_ctx = "resolvechoice4"]
## @return: resolvechoice4
## @inputs: [frame = resolvechoice3]
resolvechoice4 = ResolveChoice.apply(
    frame=resolvechoice3,
    choice="make_cols",
    transformation_ctx="resolvechoice4"
)

## Fill nulls: strings -> "NA", non-strings -> 0
df_resolved = resolvechoice4.toDF()
string_columns = [name for name, dtype in df_resolved.dtypes if dtype == 'string']
non_string_columns = [name for name, dtype in df_resolved.dtypes if dtype != 'string']
df_filled = df_resolved.fillna('NA', subset=string_columns).fillna(0, subset=non_string_columns)
filled_dynamic_frame = DynamicFrame.fromDF(df_filled, glueContext, "filled_dynamic_frame")

## @type: DataSink
## @args: [database = "aws-project",
##         table_name = "transactionsredshift_public_bulkimport"]
## @return: datasink
datasink5 = glueContext.write_dynamic_frame.from_catalog(
    frame=filled_dynamic_frame,
    database="aws-project",
    table_name="dev_public_bulkimport",
    redshift_tmp_dir=args["TempDir"],
    transformation_ctx="datasink5"
)

job.commit()
