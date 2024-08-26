# Ray Project Setup

This project uses Ray to manage VM instances for distributed computing. We will use 1 head node to orchestrate a job on a larger VM instance with a powerful CPU and 1 GPU.
## Getting Started

1. **Clone the repository:**
   
   ```bash
   git clone ray-distributed-compute.git
   cd ray-distributed-compute
   ```

2. **Install Ray:**
   
   ```bash
   pip install ray
   ```

3. **Configure AWS CLI:**
   
   ```bash
   aws configure
   ```

4. **Find Your AWS Account Number:**
   
   ```bash
   aws sts get-caller-identity --query Account --output text
   ```
   
   Note down your AWS account number, as you will need it for the next steps.

5. **Create an IAM role with full S3 access:**
   
   ```bash
   aws iam create-role --role-name ray-s3-fullaccess --assume-role-policy-document file://trust-policy.json
   ```

6. **Create an S3 bucket:**
   
   ```bash
   aws s3api create-bucket --bucket ray-bucket-model-output --region eu-central-1 --create-bucket-configuration LocationConstraint=eu-central-1
   ```

7. **Attach the S3 full access policy to the role:**
   
   ```bash
   aws iam attach-role-policy --role-name ray-s3-fullaccess --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
   ```

8. **Create an instance profile:**
   
   ```bash
   aws iam create-instance-profile --instance-profile-name ray-s3-instance-profile
   ```

9. **Add the role to the instance profile:**
   
   ```bash
   aws iam add-role-to-instance-profile --instance-profile-name ray-s3-instance-profile --role-name ray-s3-fullaccess
   ```

10. **Create a policy to allow `iam:PassRole` for `ray-autoscaler-v1`:**
    Replace `<your-account-id>` with your AWS account number.

    ```bash
    aws iam create-policy \
        --policy-name PassRolePolicy \
        --policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "iam:PassRole",
                    "Resource": "arn:aws:iam::<your-account-id>:role/ray-s3-fullaccess"
                }
            ]
        }'
    ```

11. **Attach the `PassRolePolicy` to the `ray-autoscaler-v1` role:**
    
    ```bash
    aws iam attach-role-policy \
        --role-name ray-autoscaler-v1 \
        --policy-arn arn:aws:iam::<your-account-id>:policy/PassRolePolicy
    ```

12. **Retrieve the ARN for `ray-s3-instance-profile`:**
    
    ```bash
    aws iam list-instance-profiles-for-role --role-name ray-s3-fullaccess --query 'InstanceProfiles[0].Arn' --output text
    ```
    
    Note down the retrieved ARN for use in the next steps.

13. **Update the YAML configuration:**

    Open your `raycluster.yaml` file and replace the placeholder with the ARN you retrieved:

    ```yaml
    ray.worker.default:
      resources:
        CPU: 1
        resources: 15
      node_config:
        ImageId: ami-07652eda1fbad7432
        InstanceType: p3.2xlarge
        IamInstanceProfile:
          Arn: arn:aws:iam::<your-account-id>:instance-profile/ray-s3-instance-profile
    ```

14. **Start the Ray cluster:**
    
    ```bash
    ray up raycluster.yaml
    ```

15. **Access the Ray dashboard:**
    
    ```bash
    ray dashboard raycluster.yaml
    ```

16. **Submit a Ray job:**

    Open a new terminal window and navigate to your project directory:

    ```bash
    cd <project-directory>
    ```

    Submit the Ray job:

    ```bash
    ray job submit --address http://localhost:8265 --working-dir . -- python3 remote-ray.py
    ```

17. **Check the S3 bucket:**

    When the job finishes running, head over to the specified S3 bucket (`ray-bucket-model-output`) where you should find the trained model.

## Overview

Ray is a distributed computing framework that allows you to easily scale your applications across multiple machines. In this setup, you'll use Ray to manage a head node and a larger VM instance with a powerful CPU and 1 GPU, leveraging their respective hardware capabilities to perform computational tasks efficiently.

For detailed documentation on Ray, visit the [Ray documentation](https://docs.ray.io/).