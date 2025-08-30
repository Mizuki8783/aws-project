import json
import boto3

def lambda_handler(event, context):

    print("MyEvent:")
    print(event)

    print("MyContext:")
    print(context)

    method = event['context']['http-method']

    if method == "GET":
        dynamo_client = boto3.client('dynamodb')

        im_invoiceID = event['params']['querystring']['InvoiceNo']
        print(im_invoiceID)
        response = dynamo_client.get_item(TableName = 'invoice', Key = {'InvoiceNo':{'N': im_invoiceID}})
        print(response['Item'])

        # im_customerID = event['params']['querystring']['CustomerID']
        # print(im_customerID)
        # response = dynamo_client.get_item(TableName = 'customer', Key = {'CustomerID':{'N': im_customerID}})
        # print(response['Item'])

        return {
            'statusCode': 200,
            'body': json.dumps(response['Item'])
           }

    elif method == "POST":

        client = boto3.client('kinesis')

#       mystring = event['params']['querystring']['param1']
        p_record = event['body-json']
        recordstring = json.dumps(p_record)

        response = client.put_record(
            StreamName='api-data',
            Data= recordstring,
            PartitionKey='string'
        )


        return {
            'statusCode': 200,
            'body': json.dumps(p_record)
        }
    else:
        return {
            'statusCode': 501,
            'body': json.dumps("Server Error")
        }
