import json
import logging
import sys
import time

import awsiot.greengrasscoreipc
import awsiot.greengrasscoreipc.client as gg_client
from awsiot.greengrasscoreipc.model import (
    PublishToIoTCoreRequest,
    QOS,
    SubscribeToIoTCoreRequest,
)

# Logging
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
# SDK Client
ipc_client = awsiot.greengrasscoreipc.connect()

temp = {}

def lambda_handler(event, context):
    # TODO1: Get your data
    # TODO2: Calculate max CO2 emission
    if type(event) == dict:
        event = [event]

    for record in event:
        CO2_val = float(record['vehicle_CO2'])

        if 'vehicle_id' in record:
            vehicle_stat = record['vehicle_id']
        else:
            vehicle_stat = record['device_id']

        if vehicle_stat not in temp or CO2_val > temp[vehicle_stat]:
            temp[vehicle_stat] = CO2_val

    # TODO3: Return the result
    for m in temp:
        out_topic = "vehicle/emission/result/" + m

        request = PublishToIoTCoreRequest()
        request.topic_name = out_topic
        request.payload = json.dumps({"vehicle_id": m, "max_CO2": temp[m]}).encode("utf-8")
        request.qos = QOS.AT_LEAST_ONCE
        op = ipc_client.new_publish_to_iot_core()
        op.activate(request)

    return

class Helper(gg_client.SubscribeToIoTCoreStreamHandler):
    def on_stream_event(self, event):
        e = json.loads(event.message.payload.decode("utf-8"))
        lambda_handler(e, None)

    def on_stream_error(self, error):
        return True

    def on_stream_closed(self):
        pass

request = SubscribeToIoTCoreRequest()
request.topic_name = "vehicle/emission/data"
request.qos = QOS.AT_LEAST_ONCE

helper = Helper()
operation = ipc_client.new_subscribe_to_iot_core(helper)
operation.activate(request)
operation.get_response().result(10)

while True:
    time.sleep(1)