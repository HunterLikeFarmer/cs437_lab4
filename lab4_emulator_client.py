# Import SDK packages
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import time
import json
import pandas as pd


device_st = 1
device_end = 11 # Simulates Vehicle_1 through Vehicle_10

# Path to the dataset 
data_path = "data/vehicle{}.csv"

# Path to the certificates generated in 1.5
certificate_formatter = "certificates/Vehicle_{}-certificate.pem.crt"
key_formatter = "certificates/Vehicle_{}-private.pem.key"

class MQTTClient:
    def __init__(self, device_id, cert, key):
        self.device_id = str(device_id)
        # Client ID must be unique
        self.client = AWSIoTMQTTClient(f"Vehicle_{self.device_id}") 
        
        
        self.client.configureEndpoint("a2soqojy7wmvs-ats.iot.us-east-1.amazonaws.com", 8883)
        self.client.configureCredentials("AmazonRootCA1.pem", key, cert)
        
        self.client.configureOfflinePublishQueueing(-1)  
        self.client.configureDrainingFrequency(2)  
        self.client.configureConnectDisconnectTimeout(10)  
        self.client.configureMQTTOperationTimeout(5)  
        self.client.onMessage = self.customOnMessage
        
        try:
            self.df = pd.read_csv(data_path.format(self.device_id))
            self.data_iterator = self.df.iterrows()
        except FileNotFoundError:
            print(f"Warning: No CSV found for vehicle {self.device_id}. It will not send data.")
            self.data_iterator = None

    def customOnMessage(self, message):
        print("\n **RECEIVED** Client {} received payload {} from topic {}".format(
            self.device_id, message.payload.decode('utf-8'), message.topic))

    def customSubackCallback(self, mid, data):
        pass

    def customPubackCallback(self, mid):
        pass

    def publish(self, topic="vehicle/emission/data"):
        # If no CSV exists for this vehicle, skip publishing
        if self.data_iterator is None:
            return

        try:
            # Get exactly one row of data per function call
            index, row = next(self.data_iterator)
            
            # Create a JSON payload 
            payload_dict = row.to_dict()
            payload_dict['device_id'] = f"Vehicle_{self.device_id}"
            payload = json.dumps(payload_dict)
            
            print(f"Publishing from Vehicle_{self.device_id}: {payload}")
            self.client.publishAsync(topic, payload, 1, ackCallback=self.customPubackCallback)
            
        except StopIteration:
            print(f"Vehicle_{self.device_id} has reached the end of its CSV data.")


print("Initializing MQTTClients...")
clients = []

for device_id in range(device_st, device_end):
    cert_path = certificate_formatter.format(device_id)
    key_path = key_formatter.format(device_id)
    
    # Instantiate the client
    client = MQTTClient(device_id, cert_path, key_path)
    client.client.connect()
    
    client.client.subscribeAsync("vehicle/emission/data", 1, ackCallback=client.customSubackCallback)
    
    clients.append(client)

while True:
    print("\nPress 's' to send one data point per vehicle, or 'd' to disconnect:")
    x = input().strip().lower()
    
    if x == "s":
        for c in clients:
            c.publish()
    elif x == "d":
        for c in clients:
            c.client.disconnect()
        print("All devices disconnected")
        break
    else:
        print("Invalid key pressed.")
    
    time.sleep(1)