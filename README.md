# Serverless Attendance Management System

React (Vite) + Python Lambda + DynamoDB, provisioned with Terraform.

## Prerequisites
AWS CLI configured, Terraform >= 1.6, Python 3.12, Node 18+.

## Backend
    ./scripts/build.sh          # packages Lambda code + dependencies
    cd infra
    terraform init
    terraform apply
Copy the `api_url` output. Re-run `./scripts/build.sh` before `terraform apply` whenever backend code changes.

## Frontend
    cd frontend
    cp .env.example .env     # paste api_url as VITE_API_URL
    npm install
    npm run dev

Check the API: `curl <api_url>/health`
