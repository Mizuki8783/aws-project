## AWS Data Engineering Project: Stream + Batch Pipelines

This repository implements both a real-time streaming pipeline and a scheduled batch pipeline on AWS. It demonstrates end-to-end ingestion, fan-out processing, and storage across DynamoDB, S3, and Redshift, with an AWS Glue job for batch transformations.

![Dataflow](assets/dataflow-diagram.png)

### Stream pipeline
- **Client → API Gateway (POST)**: Client sends JSON events.
- **Lambda `kinesis_api`**: Writes the request body to Kinesis stream `api-data`. Also supports a GET to query DynamoDB by `InvoiceNo`.
- **Kinesis fan-out consumers**:
  - **Lambda `write_kinesis_to_dynamodb`**: Upserts into DynamoDB tables `customer` and `invoice`.
  - **Lambda `write_kinesis_to_s3`**: Appends raw events to S3 bucket `mn-de-project` under `aws-project/kinesis-stream/`.
  - **(Optional) Firehose → Redshift**: Stream data delivery into Redshift (configure in your AWS account).

### Batch pipeline
- **Glue Job `bulkimport_s3_redshift.py`**: Periodically reads curated/raw data in S3 via AWS Glue Data Catalog and loads it into Redshift table `dev_public_bulkimport`, with null-handling and schema mapping.

## Repository layout
- `code/client.py`: Simple Python client that POSTs rows from `data/data.csv` to the API Gateway endpoint.
- `code/lambda/kinesis_api.py`: API Lambda handling POST (write to Kinesis) and GET (read from DynamoDB by `InvoiceNo`).
- `code/lambda/write_kinesis_to_dynamodb.py`: Kinesis consumer that writes to DynamoDB tables `customer` and `invoice`.
- `code/lambda/write_kinesis_to_s3.py`: Kinesis consumer that writes raw events to S3 (`mn-de-project/aws-project/kinesis-stream/`).
- `code/glue/bulkimport_s3_redshift.py`: Glue ETL from S3 (catalog table `s3_bulkimport`) to Redshift (`dev_public_bulkimport`).
- `code/redshift/check_cost.sql`: Helper SQL to estimate Amazon Redshift Serverless costs by day and query.
- `data/`: Sample CSVs.
- `_tmp/Code/Module-*`: Reference IAM policies, Lambda snippets, and SQL used during module work.

## Data contracts
### Event payload (stream)
The client sends rows from `data/data.csv` as JSON. Example payload:

```json
{
  "InvoiceNo": "536365",
  "StockCode": "85123A",
  "Description": "WHITE HANGING HEART T-LIGHT HOLDER",
  "Quantity": 6,
  "InvoiceDate": "12/1/2010 8:26",
  "UnitPrice": 2.55,
  "CustomerID": "17850",
  "Country": "United Kingdom"
}
```

### DynamoDB access (query via GET)
- Endpoint expects querystring parameter `InvoiceNo` and returns the raw DynamoDB item from table `invoice`.

## AWS components and configuration
### API Gateway + Lambda `kinesis_api`
- POST: Expects JSON body passed through to Lambda. Lambda writes to Kinesis stream `api-data`.
- GET: Expects `?InvoiceNo=...`. Lambda fetches item from DynamoDB table `invoice`.
- Note: If using REST API (non-proxy), configure an `application/json` mapping template so Lambda receives fields like `context.http-method`, `body-json`, and `params.querystring.InvoiceNo` as referenced in the code.

### Kinesis Data Stream
- Stream name: `api-data` (update in `code/lambda/kinesis_api.py` if you choose a different name).

### DynamoDB tables
- `invoice` with partition key `InvoiceNo` (String).
- `customer` with partition key `CustomerID` (String).
- The Kinesis consumer Lambda stores:
  - In `invoice`: a wide row keyed by `InvoiceNo`, attributes named by `StockCode` containing the remaining fields as JSON strings.
  - In `customer`: per-customer attributes keyed by `InvoiceNo` (placeholder value in code; adjust as needed for your UI/analytics).

### S3 bucket
- Bucket: `mn-de-project` (change in `code/lambda/write_kinesis_to_s3.py` if needed).
- Prefix for streaming dump: `aws-project/kinesis-stream/`.

### Firehose → Redshift (optional)
- Configure Kinesis Data Firehose to deliver streaming data to Redshift, or rely on the Glue batch path below.

### AWS Glue → Redshift (batch)
- Glue Data Catalog database: `aws-project`.
- Source table: `s3_bulkimport` (points to S3 dataset).
- Target Redshift table (via Catalog integration): `dev_public_bulkimport`.
- Script applies mapping, selects fields, resolves choices, fills nulls, and writes to Redshift using a temporary S3 dir (`--TempDir`).

## Getting started
### Prerequisites
- AWS account with permissions for API Gateway, Lambda, Kinesis, DynamoDB, S3, Glue, and Redshift.
- Python 3.13+ for the sample client.
- Optionally refer to `_tmp/Code/Module-06` policies as starting points for IAM.

### Deploy high-level steps
1) Create S3 bucket for raw/curated data (or reuse `mn-de-project`).
2) Create DynamoDB tables `invoice` (PK `InvoiceNo`, String) and `customer` (PK `CustomerID`, String).
3) Create Kinesis stream `api-data`.
4) Deploy Lambdas:
   - `kinesis_api` (invoke by API Gateway; Kinesis write permissions).
   - `write_kinesis_to_dynamodb` (triggered by Kinesis; DynamoDB write permissions).
   - `write_kinesis_to_s3` (triggered by Kinesis; S3 PutObject permissions; update bucket name if needed).
5) Create API Gateway (REST or HTTP). If not using Lambda proxy integration, add an `application/json` mapping template so the Lambda receives `context/http-method`, `body-json`, and `params/querystring` fields.
6) (Optional) Configure Firehose to Redshift.
7) Set up Glue Data Catalog database `aws-project` and table `s3_bulkimport` pointing to your S3 data; then create/run the Glue job using `code/glue/bulkimport_s3_redshift.py`.

### Local client (send events)
1) Install dependencies (choose one):
   - pip: `python -m venv .venv && source .venv/bin/activate && pip install -e .`
   - uv: `uv sync`
2) Create `.env` in repo root:
```
CLIENT_TARGET_ENDPOINT=https://your-api-id.execute-api.your-region.amazonaws.com/your-stage/your-resource
```
3) Run: `python code/client.py`

### Example cURL
- POST an event:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
        "InvoiceNo":"536365",
        "StockCode":"85123A",
        "Description":"WHITE HANGING HEART T-LIGHT HOLDER",
        "Quantity":6,
        "InvoiceDate":"12/1/2010 8:26",
        "UnitPrice":2.55,
        "CustomerID":"17850",
        "Country":"United Kingdom"
      }' \
  "$CLIENT_TARGET_ENDPOINT"
```

- GET by invoice number:
```bash
curl "$CLIENT_TARGET_ENDPOINT?InvoiceNo=536365"
```

## Operations
- Redshift cost analysis: see `code/redshift/check_cost.sql` and replace placeholders (e.g., RPU price, date) before running.
- Error hints (from comments in `code/client.py`):
  - If you see 200 from client but Lambda logs `KeyError: 'context'`, your API mapping template is missing.
  - For 403 from API Gateway, ensure the deployed resource path (e.g., `/hello`) is included in the URL.

## Configuration summary (update as needed)
- Kinesis stream: `api-data`.
- DynamoDB tables: `invoice`, `customer`.
- S3 bucket/prefix: `mn-de-project/aws-project/kinesis-stream/`.
- Glue catalog: db `aws-project`, tables `s3_bulkimport` → Redshift `dev_public_bulkimport`.

## Security and costs
- Apply least-privilege IAM for all services (see `_tmp/Code/Module-06` for examples).
- Consider S3 encryption, DynamoDB PITR, KMS for streams, and VPC endpoints for private traffic.
- Monitor costs for Kinesis shards, Lambda invocations, S3 storage/requests, and Redshift (use the SQL helper).
