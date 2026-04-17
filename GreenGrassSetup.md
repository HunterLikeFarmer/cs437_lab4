# Lab 4 — Step 1.7: GreenGrass V2 on EC2 — Complete Walkthrough

## Overview

This document captures every operation performed to complete Step 1.7 of IoT Lab 4. The goal was to set up AWS IoT GreenGrass V2 on an EC2 instance acting as the GreenGrass Core, then connect a client device (Vehicle_1) through the core to the AWS IoT Cloud.

**Architecture:**
```
Vehicle_1 (client device on EC2) → FinalGreengrassCore (EC2, port 8883) → AWS IoT Cloud
```

**AWS Account ID:** 826063979548
**Region:** us-east-1
**Core Device Thing Name:** FinalGreengrassCore
**Client Device Thing Name:** Vehicle_1

---

## Part A: Launch and Configure the EC2 Instance

### 1. Launch an EC2 Instance

- Instance type: t2.micro (or larger)
- AMI: Ubuntu 24.04 LTS (or Amazon Linux 2023)
- Key pair: Use an existing or create a new one for SSH access
- Security group inbound rules:
  - Port 22 (SSH) — your IP
  - Port 8883 (MQTT) — 0.0.0.0/0 (or restrict to client IP)
  - Port 443 (HTTPS) — 0.0.0.0/0

### 2. SSH into the EC2 Instance

```bash
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

### 3. Install Java (required by GreenGrass V2)

```bash
# Ubuntu
sudo apt update
sudo apt install default-jdk -y

# Verify
java -version
```

### 4. Create the Default GreenGrass System User and Group

```bash
sudo useradd --system --create-home ggc_user
sudo groupadd --system ggc_group
```

---

## Part B: Provide AWS Credentials to the EC2 Instance

The GreenGrass installer needs credentials to auto-provision IoT resources.

```bash
export AWS_ACCESS_KEY_ID=<your_access_key_id>
export AWS_SECRET_ACCESS_KEY=<your_secret_access_key>
```

---

## Part C: Download and Install GreenGrass V2 Core Software

### 1. Download the GreenGrass Nucleus

```bash
curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip > greengrass-nucleus-latest.zip
```

### 2. Unzip

```bash
unzip greengrass-nucleus-latest.zip -d GreengrassInstaller && rm greengrass-nucleus-latest.zip
```

### 3. Run the Installer with Automatic Provisioning

```bash
sudo -E java -Droot="/greengrass/v2" -Dlog.store=FILE \
  -jar ./GreengrassInstaller/lib/Greengrass.jar \
  --aws-region us-east-1 \
  --thing-name FinalGreengrassCore \
  --thing-group-name MyGreengrassCoreGroup \
  --thing-policy-name GreengrassV2IoTThingPolicy \
  --tes-role-name GreengrassV2TokenExchangeRole \
  --tes-role-alias-name GreengrassCoreTokenExchangeRoleAlias \
  --component-default-user ggc_user:ggc_group \
  --provision true \
  --setup-system-service true \
  --deploy-dev-tools true
```

**Key flags explained:**
- `--provision true` — auto-creates the IoT Thing, certificates, policy, and IAM role
- `--setup-system-service true` — registers GreenGrass as a systemd service (runs on boot)
- `--deploy-dev-tools true` — installs the GreenGrass CLI on the device

### 4. Verify GreenGrass Is Running

```bash
sudo systemctl status greengrass.service
```

Check logs:
```bash
sudo tail -f /greengrass/v2/logs/greengrass.log
```

---

## Part D: Create the Client Device (Vehicle_1) in AWS IoT

### 1. Create the Thing

This was done in Section 1.3/1.5 of the lab. The Thing `Vehicle_1` was created either through the AWS Console or via boto3, along with its certificate and private key files:
- `Vehicle_1-certificate.pem.crt`
- `Vehicle_1-private.pem.key`

### 2. Download the Amazon Root CA (if not already done)

```bash
curl -o AmazonRootCA1.pem https://www.amazontrust.com/repository/AmazonRootCA1.pem
```

---

## Part E: Configure the Client Device IoT Policy

The IoT policy attached to Vehicle_1's certificate must include `greengrass:Discover`. The policy named `437` was configured with:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iot:Connect",
        "iot:Publish",
        "iot:Subscribe",
        "iot:Receive",
        "greengrass:Discover",
        "greengrass:*"
      ],
      "Resource": "*"
    }
  ]
}
```

To set this via CLI:

```bash
aws iot create-policy-version --policy-name 437 --set-as-default \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "iot:Connect",
          "iot:Publish",
          "iot:Subscribe",
          "iot:Receive",
          "greengrass:Discover",
          "greengrass:*"
        ],
        "Resource": "*"
      }
    ]
  }' --region us-east-1
```

---

## Part F: Associate Vehicle_1 with the GreenGrass Core Device

```bash
aws greengrassv2 batch-associate-client-device-with-core-device \
  --core-device-thing-name FinalGreengrassCore \
  --entries thingName=Vehicle_1 \
  --region us-east-1
```

Or do this via the console: **IoT Greengrass → Core devices → FinalGreengrassCore → Client devices tab → Configure cloud discovery → Step 2: Associate client devices → Add Vehicle_1.**

---

## Part G: Set Up the GreenGrass Service Role (Critical — Caused 401 Error)

Without this account-level service role, the discovery API rejects all client device requests with HTTP 401.

### 1. Create the IAM Role

```bash
aws iam create-role --role-name GreengrassServiceRole \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":{"Service":"greengrass.amazonaws.com"},
      "Action":"sts:AssumeRole"
    }]
  }'
```

### 2. Attach the Required Policy

```bash
aws iam attach-role-policy --role-name GreengrassServiceRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGreengrassResourceAccessRolePolicy
```

### 3. Associate the Role with Your Account

```bash
aws greengrassv2 associate-service-role-to-account \
  --role-arn arn:aws:iam::826063979548:role/GreengrassServiceRole \
  --region us-east-1
```

### 4. Verify

```bash
aws greengrassv2 get-service-role-for-account --region us-east-1
```

---

## Part H: Deploy Client Device Components to the Core

Three components were deployed via the console. The IP Detector was skipped in favor of manually setting connectivity info (see Part I).

### Components Deployed

| Component | Version | Purpose |
|-----------|---------|---------|
| `aws.greengrass.clientdevices.Auth` | 2.5.5 | Authenticates client devices and authorizes MQTT actions |
| `aws.greengrass.clientdevices.mqtt.Moquette` | 2.3.7 | Runs a local MQTT broker on port 8883 |
| `aws.greengrass.clientdevices.mqtt.Bridge` | 2.3.2 | Relays messages between local MQTT and AWS IoT Core |

### Deployment via Console

1. Go to **AWS IoT Greengrass Console → Core devices → FinalGreengrassCore**
2. Click **Client devices tab → Configure cloud discovery**
3. Configure each component:

**Client Device Auth configuration:**
```json
{
  "deviceGroups": {
    "formatVersion": "2021-03-05",
    "definitions": {
      "MyDeviceGroup": {
        "selectionRule": "thingName: *",
        "policyName": "MyClientDevicePolicy"
      }
    },
    "policies": {
      "MyClientDevicePolicy": {
        "AllowConnect": {
          "statementDescription": "Allow all client devices to connect.",
          "operations": ["mqtt:connect"],
          "resources": ["*"]
        },
        "AllowPublish": {
          "statementDescription": "Allow client devices to publish to all topics.",
          "operations": ["mqtt:publish"],
          "resources": ["*"]
        },
        "AllowSubscribe": {
          "statementDescription": "Allow client devices to subscribe to all topics.",
          "operations": ["mqtt:subscribe"],
          "resources": ["*"]
        }
      }
    }
  }
}
```

**MQTT Bridge configuration:**
```json
{
  "mqttTopicMapping": {
    "DeviceDataToCloud": {
      "topic": "clients/+/hello/world",
      "source": "LocalMqtt",
      "target": "IotCore"
    }
  }
}
```

**Moquette:** No configuration needed (defaults to port 8883).

### Deployment via CLI (Alternative)

```bash
aws greengrassv2 create-deployment \
  --target-arn arn:aws:iot:us-east-1:826063979548:thing/FinalGreengrassCore \
  --components '{
    "aws.greengrass.clientdevices.Auth": {
      "componentVersion": "2.5.5",
      "configurationUpdate": {}
    },
    "aws.greengrass.clientdevices.mqtt.Moquette": {
      "componentVersion": "2.3.7"
    },
    "aws.greengrass.clientdevices.mqtt.Bridge": {
      "componentVersion": "2.3.2",
      "configurationUpdate": {}
    }
  }' \
  --region us-east-1
```

### Verify Deployment

```bash
aws greengrassv2 list-installed-components \
  --core-device-thing-name FinalGreengrassCore --region us-east-1
```

All three components should show `"lifecycleState": "RUNNING"`.

---

## Part I: Set Core Device Connectivity Info (Critical — Caused 404 Error)

The IP Detector component was not deployed, so the discovery endpoint had no connectivity information for the core and returned HTTP 404 to clients. The fix was to manually register the EC2 public IP.

### 1. Get EC2 Public IP

```bash
curl -s http://169.254.169.254/latest/meta-data/public-ipv4
# Output: 54.90.119.100
```

### 2. Manually Set Connectivity Info

```bash
aws greengrass update-connectivity-info \
  --thing-name FinalGreengrassCore \
  --connectivity-info '[{
    "Id": "public_ip",
    "HostAddress": "54.90.119.100",
    "PortNumber": 8883,
    "Metadata": ""
  }]' \
  --region us-east-1
```

**Important:** The keys must be PascalCase (`Id`, `HostAddress`, `PortNumber`, `Metadata`), not camelCase.

### 3. Verify

```bash
aws greengrass get-connectivity-info \
  --thing-name FinalGreengrassCore --region us-east-1
```

Expected output:
```json
{
    "ConnectivityInfo": [
        {
            "HostAddress": "54.90.119.100",
            "Id": "public_ip",
            "Metadata": "",
            "PortNumber": 8883
        }
    ]
}
```

**Note:** If you stop/start the EC2 instance, the public IP changes. You must re-run the `update-connectivity-info` command with the new IP. Consider using an Elastic IP to avoid this.

---

## Part J: Install the AWS IoT Device SDK and Run the Client

### 1. Install the SDK

```bash
git clone https://github.com/aws/aws-iot-device-sdk-python-v2.git
cd aws-iot-device-sdk-python-v2
python3 -m pip install --user .
cd ..
```

### 2. Run the Discovery Script

The `basic_discovery.py` script (provided separately) uses the AWS IoT Device SDK's `DiscoveryClient` to find the GreenGrass core, then connects via MQTT to publish and subscribe.

```bash
python3 basic_discovery.py \
  --thing_name Vehicle_1 \
  --cert Vehicle_1-certificate.pem.crt \
  --key Vehicle_1-private.pem.key \
  --region us-east-1 \
  --topic "clients/Vehicle_1/hello/world" \
  --message "Hello from FinalGreengrassCore!"
```

### 3. Successful Output

```
Performing greengrass discovery...
  Thing name: Vehicle_1
  Region: us-east-1
  Cert: /home/ubuntu/437/Vehicle_1-certificate.pem.crt
  Key: /home/ubuntu/437/Vehicle_1-private.pem.key
  Discovery endpoint: https://greengrass-ats.iot.us-east-1.amazonaws.com:8443

Discovery succeeded! Received Greengrass core info.
  Number of GG groups: 1
  Group: greengrassV2-coreDevice-FinalGreengrassCore
    Core: arn:aws:iot:us-east-1:826063979548:thing/FinalGreengrassCore
      Endpoint: 54.90.119.100:8883
Trying core arn:aws:iot:us-east-1:826063979548:thing/FinalGreengrassCore at host 54.90.119.100 port 8883
Connected!
Publish received on topic clients/Vehicle_1/hello/world
b'{"message": "Hello from FinalGreengrassCore!", "sequence": 0}'
Successfully published to topic clients/Vehicle_1/hello/world with payload `{"message": "Hello from FinalGreengrassCore!", "sequence": 0}`
...
Successfully published to topic clients/Vehicle_1/hello/world with payload `{"message": "Hello from FinalGreengrassCore!", "sequence": 9}`
```

### 4. Verify Messages Reach AWS IoT Core

1. Go to **AWS IoT Console → Test → MQTT test client**
2. Subscribe to topic filter: `clients/+/hello/world`
3. Run the discovery script again
4. Messages should appear in the MQTT test client

---

## Part K: Diagnostic Script (diagnose.sh)

This script was used to debug the 401 and 404 errors encountered during setup.

```bash
#!/bin/bash

echo -e "\n=== STEP 1: Describe Thing ==="
aws iot describe-thing --thing-name Vehicle_1 --region us-east-1

echo -e "\n=== STEP 2: List Principals ==="
CERT_ARN=$(aws iot list-thing-principals --thing-name Vehicle_1 --region us-east-1 --query 'principals[0]' --output text)
echo "Found ARN: $CERT_ARN"

echo -e "\n=== STEP 3: Describe Certificate ==="
CERT_ID=$(echo $CERT_ARN | awk -F'/' '{print $2}')
aws iot describe-certificate --certificate-id $CERT_ID --region us-east-1 --query 'certificateDescription.[status, certificatePem]'

echo -e "\n=== STEP 4: Local File Fingerprint ==="
openssl x509 -noout -fingerprint -in Vehicle_1-certificate.pem.crt

echo -e "\n=== STEP 5: List Attached Policies ==="
aws iot list-attached-policies --target $CERT_ARN --region us-east-1

echo -e "\n=== STEP 6: Get Policy Document ==="
POLICY_NAME=$(aws iot list-attached-policies --target $CERT_ARN --region us-east-1 --query 'policies[0].policyName' --output text)
aws iot get-policy --policy-name $POLICY_NAME --region us-east-1 --query 'policyDocument'

echo -e "\n=== STEP 7: Check Core Association ==="
aws greengrassv2 list-client-devices-associated-with-core-device --core-device-thing-name FinalGreengrassCore --region us-east-1

echo -e "\n=== STEP 8: Raw Curl Test ==="
curl -v --cert Vehicle_1-certificate.pem.crt --key Vehicle_1-private.pem.key https://greengrass-ats.iot.us-east-1.amazonaws.com:8443/greengrass/discover/thing/Vehicle_1
```

### Additional Verification Commands

```bash
# Cert file matches AWS? (SHA-256 fingerprint should match certificate ID)
openssl x509 -noout -fingerprint -sha256 -in Vehicle_1-certificate.pem.crt | tr -d ':' | awk -F'=' '{print tolower($2)}'

# Cert and key match each other? (both md5sums must be identical)
openssl x509 -noout -modulus -in Vehicle_1-certificate.pem.crt | md5sum
openssl rsa  -noout -modulus -in Vehicle_1-private.pem.key     | md5sum

# Service role configured?
aws greengrassv2 get-service-role-for-account --region us-east-1

# Components running on core?
aws greengrassv2 list-installed-components --core-device-thing-name FinalGreengrassCore --region us-east-1

# Connectivity info registered?
aws greengrass get-connectivity-info --thing-name FinalGreengrassCore --region us-east-1

# Port reachable?
nc -zv 54.90.119.100 8883 -w 5
```

---

## Issues Encountered and Resolutions

### Issue 1: HTTP 401 Unauthorized from Discovery Endpoint

**Symptom:** `DiscoveryException: response_code=401`

**Root Cause:** The GreenGrass service role was not associated with the AWS account. This account-level role is required for the discovery API to verify client device identities.

**Resolution:** Created the `GreengrassServiceRole` IAM role, attached the `AWSGreengrassResourceAccessRolePolicy`, and associated it with the account via `aws greengrassv2 associate-service-role-to-account`.

### Issue 2: HTTP 404 Not Found from Discovery Endpoint

**Symptom:** `DiscoveryException: response_code=404`

**Root Cause:** No connectivity information was registered for the core device. The IP Detector component was not deployed, so the cloud had no IP address to return to discovering clients.

**Resolution:** Manually set the connectivity info using `aws greengrass update-connectivity-info` with the EC2 public IP and port 8883.

### Issue 3: PascalCase Keys for update-connectivity-info

**Symptom:** `ParamValidation: Unknown parameter "id", must be one of: HostAddress, Id, Metadata, PortNumber`

**Root Cause:** The AWS CLI expects PascalCase keys (`Id`, `HostAddress`, `PortNumber`, `Metadata`), not camelCase.

**Resolution:** Changed keys from `"id"`, `"hostAddress"`, `"portNumber"` to `"Id"`, `"HostAddress"`, `"PortNumber"`.

---

## Important Reminders

1. **EC2 Public IP changes on stop/start.** If you stop and restart your EC2 instance, re-run `update-connectivity-info` with the new public IP. Consider allocating an Elastic IP.

2. **Tear down resources when done.** AWS IoT and GreenGrass incur costs. Delete Things, certificates, deployments, and terminate EC2 instances when finished.

3. **Security group.** Ensure EC2 security group allows inbound TCP on port 8883 from wherever the client device runs.

4. **GreenGrass logs.** Check logs at `/greengrass/v2/logs/greengrass.log` and component-specific logs in `/greengrass/v2/logs/` for debugging.