# Serverless Attendance Management System

React (Vite) + Python Lambda + DynamoDB, deployed with AWS SAM.

## Prerequisites
AWS CLI configured, AWS SAM CLI, Python 3.12, Node 18+.

## Backend
    sam build
    sam deploy --guided --parameter-overrides JwtSecret=<32+ random chars>
Copy the `ApiUrl` output.

## Frontend
    cd frontend
    cp .env.example .env     # paste ApiUrl as VITE_API_URL
    npm install
    npm run dev

Check the API: `curl <ApiUrl>/health`
