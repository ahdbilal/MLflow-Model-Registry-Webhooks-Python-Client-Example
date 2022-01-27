# Databricks notebook source
# MAGIC %md
# MAGIC # MLflow Model Registry Webhooks Python Client Example

# COMMAND ----------

# MAGIC %md ## Install MLflow and the Webhooks Client

# COMMAND ----------

# MAGIC %pip install mlflow

# COMMAND ----------

# MAGIC %pip install databricks-registry-webhooks

# COMMAND ----------

# MAGIC %md ## Create webhooks, test them, and confirm their presence in the list of all webhooks

# COMMAND ----------

## SETUP: Fill in variables
access_token = '<INSERT YOUR ACCESS TOKEN HERE>'
model_name = '<INSERT YOUR REGISTERED MODEL NAME HERE>'
job_id = 0 # INSERT ID OF PRE-DEFINED JOB
url = '<INSERT YOUR INCOMING WEBHOOK URL HERE >'

# COMMAND ----------

from databricks_registry_webhooks import RegistryWebhooksClient, JobSpec, HttpUrlSpec

# COMMAND ----------

# Create a HTTP webhook that will create alerts about registered models created
http_url_spec = HttpUrlSpec(url=url, secret="secret_string")
http_webhook = RegistryWebhooksClient().create_webhook(
  events=["TRANSITION_REQUEST_CREATED", "MODEL_VERSION_CREATED", "MODEL_VERSION_TRANSITIONED_STAGE"],
  http_url_spec=http_url_spec,
  model_name=model_name
)
http_webhook

# COMMAND ----------

# Test the HTTP webhook
RegistryWebhooksClient().test_webhook(id=http_webhook.id)

# COMMAND ----------

# Create a Job webhook
job_spec = JobSpec(job_id=job_id, access_token=access_token)
job_webhook = RegistryWebhooksClient().create_webhook(
  events=["TRANSITION_REQUEST_CREATED"],
  job_spec=job_spec,
  model_name=model_name
)
job_webhook

# COMMAND ----------

# Test the Job webhook
RegistryWebhooksClient().test_webhook(id=job_webhook.id)

# COMMAND ----------

# List all webhooks and verify webhooks just created are shown in the list
webhooks_list = RegistryWebhooksClient().list_webhooks(
  events=["TRANSITION_REQUEST_CREATED", "MODEL_VERSION_CREATED", "MODEL_VERSION_TRANSITIONED_STAGE"]
)
print(webhooks_list[:10])
assert http_webhook.id in [w.id for w in webhooks_list]
assert job_webhook.id in [w.id for w in webhooks_list]

# COMMAND ----------

# MAGIC %md ## Create a transition request to trigger webhooks and then clean up webhooks

# COMMAND ----------

import mlflow
from mlflow.utils.rest_utils import http_request
import json
def client():
  return mlflow.tracking.client.MlflowClient()

host_creds = client()._tracking_client.store.get_host_creds()
def mlflow_call_endpoint(endpoint, method, body='{}'):
  if method == 'GET':
      response = http_request(
          host_creds=host_creds, endpoint="/api/2.0/mlflow/{}".format(endpoint), method=method, params=json.loads(body))
  else:
      response = http_request(
          host_creds=host_creds, endpoint="/api/2.0/mlflow/{}".format(endpoint), method=method, json=json.loads(body))
  return response.json()

# COMMAND ----------

# Create a transition request to staging and then approve the request
transition_request_body = {'name': model_name, 'version': 1, 'stage': 'Staging'}
mlflow_call_endpoint('transition-requests/create', 'POST', json.dumps(transition_request_body))
transition_request_body = {'name': model_name, 'version': 1, 'stage': 'Staging', 'archive_existing_versions': 'true'}
mlflow_call_endpoint('transition-requests/approve', 'POST', json.dumps(transition_request_body))

# COMMAND ----------

# Delete all webhooks
for webhook in webhooks_list:
  RegistryWebhooksClient().delete_webhook(webhook.id)

# COMMAND ----------

# Verify webhook deletion
webhooks_list = RegistryWebhooksClient().list_webhooks(
  events=["TRANSITION_REQUEST_CREATED", "MODEL_VERSION_CREATED", "MODEL_VERSION_TRANSITIONED_STAGE"]
)
print(webhooks_list[:10])
assert http_webhook.id not in [w.id for w in webhooks_list]
assert job_webhook.id not in [w.id for w in webhooks_list]
