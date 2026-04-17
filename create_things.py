import boto3
import json
import os

# Initialize the IoT client using your credentials and region
client = boto3.client('iot', region_name='us-east-1') 

# Configuration Variables
thingGroupName = '437_group' 
defaultPolicyName = '437' 
numberOfDevices = 10 

# Create a folder to store the downloaded certificates
if not os.path.exists('certificates'):
    os.makedirs('certificates')

for i in range(1, numberOfDevices + 1):
    thingName = f"Vehicle_{i}"
    print(f"Creating {thingName}...")

    # 1. create_thing()
    thingResponse = client.create_thing(thingName=thingName)
    thingArn = thingResponse['thingArn']

    # 2. create_keys_and_certificate() 
    certResponse = client.create_keys_and_certificate(setAsActive=True)
    certArn = certResponse['certificateArn']
    
    # Important: Save the keys locally. Needed for the emulator in 1.6
    with open(f"certificates/{thingName}-certificate.pem.crt", "w") as f:
        f.write(certResponse['certificatePem'])
    with open(f"certificates/{thingName}-private.pem.key", "w") as f:
        f.write(certResponse['keyPair']['PrivateKey'])
    with open(f"certificates/{thingName}-public.pem.key", "w") as f:
        f.write(certResponse['keyPair']['PublicKey'])

    # 3. attach_policy() 
    client.attach_policy(
        policyName=defaultPolicyName,
        target=certArn
    )

    # 4. attach_thing_principal() 
    client.attach_thing_principal(
        thingName=thingName,
        principal=certArn
    )

    # 5. add_thing_to_thing_group() 
    client.add_thing_to_thing_group(
        thingGroupName=thingGroupName,
        thingGroupArn='', 
        thingArn=thingArn
    )

print("Creation complete!")