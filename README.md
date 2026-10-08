# Serverless Attendance Management System

A web app where **teachers mark attendance** and **students view their own**. The backend is serverless (Lambda, DynamoDB, API Gateway). The website is served by one small EC2 server running nginx.

## What it does

| Role | Can do |
|------|--------|
| Student | Register, sign in, see **only their own** attendance (per class percentage, flagged below 75%, and day by day) |
| Teacher | Register (needs a sign-up code), create classes, add students by username, mark present/absent for any date, correct earlier marks, view a class on any day |
| Everyone | Sign in with **email or username** + password. Forgot password? Reset it with a **6-digit code sent to the registered mobile number** |

## How it works

```
Browser --> EC2 server (nginx serves the React app)
   |
   +--> API Gateway --> Lambda (Python) --> DynamoDB (4 tables)
                              |
                              +--> SNS (sends the OTP text message)

Deploying the website:  your computer --> S3 bucket --> (SSM command) --> EC2 server
```

| Part | Technology |
|------|-----------|
| Website | React (Vite), served by **nginx on one EC2 server** (files delivered via a private S3 bucket and SSM, no SSH) |
| API | API Gateway (HTTP API) + 3 Python 3.12 Lambda functions |
| Database | DynamoDB: `users`, `classes`, `attendance`, `otp` |
| Login | Passwords hashed with scrypt, signed JWT tokens, role checked on every request |
| OTP | Amazon SNS text message, code stored only as a hash, expires in 5 minutes |
| Infrastructure | Terraform (everything is created by code) |
| Alerts | CloudWatch alarms emailed through SNS |

## Project structure

```
attendance-system/
├── README.md
├── .github/workflows/      CI/CD: ci.yml (checks) and deploy.yml (auto-deploy)
├── infra/                  Terraform: builds all AWS resources
│   ├── versions.tf         tools and region
│   ├── variables.tf        settings you can change
│   ├── dynamodb.tf         database tables
│   ├── lambda.tf           Lambda functions and their permissions
│   ├── api.tf              API URLs and CORS
│   ├── frontend.tf         EC2 web server + S3 upload bucket
│   ├── user_data.sh.tftpl  nginx setup that runs when the server first starts
│   ├── alarms.tf           error alerts
│   ├── sns.tf              SMS spend limit
│   ├── github_oidc.tf      lets GitHub Actions deploy without stored keys
│   └── outputs.tf          URLs printed after deploy
├── backend/                Python code
│   ├── common/             shared helpers (responses, db, auth, sms)
│   ├── functions/          health/, auth/, attendance/
│   └── tests/              automated tests
├── frontend/               React app (src/pages, src/api, src/context)
└── scripts/
    ├── deploy.sh           deploy everything
    ├── deploy-frontend.sh  publish only the website
    ├── tf-init.sh          create the state bucket and run terraform init
    └── build.sh            package the Lambda code
```

## Prerequisites

### 1. An AWS account
Create one at aws.amazon.com. Turn on MFA for the root user, then create a normal **IAM user** (do not use root keys) with programmatic access. For a personal learning account, the `AdministratorAccess` policy is the simplest. In the Billing console, create a **budget alert** (for example 5 USD) so you are warned about any cost.

### 2. Tools on your computer

| Tool | Version | Check with | Download |
|------|---------|-----------|----------|
| Git Bash (Windows only) or any Mac/Linux terminal | any | `bash --version` | git-scm.com |
| AWS CLI | v2 | `aws --version` | aws.amazon.com/cli |
| Terraform | 1.10 or newer | `terraform -version` | developer.hashicorp.com/terraform/install |
| Node.js (includes npm) | 18 or newer | `node -v` | nodejs.org (LTS) |
| Python | 3.9 or newer | `python3 --version` (or `python --version`) | python.org |

Windows users: run every command below in **Git Bash** (or WSL), not in Command Prompt.

### 3. Connect the AWS CLI to your account
```
aws configure
```
Enter your IAM user's access key, secret key, region (the default used here is `ap-south-1`; if you choose another, also set it with `-var region=...` below), and output format `json`. Test with:
```
aws sts get-caller-identity
```

## Run from scratch

### Step 1: Get the code
```
git clone https://github.com/Uday-Kumar033/Project-Serverless-Attendance.git
cd Project-Serverless-Attendance
```

### Step 2: Deploy everything with one command
```
bash scripts/deploy.sh
```
This runs, in order: package the Python code, create the Terraform state bucket and run `terraform init`, `terraform apply`, then build and upload the website. Terraform shows a plan and asks you to type `yes`.

- The **first deploy takes about 5 to 8 minutes** (the server needs a few minutes to start and install nginx). Later deploys are faster.
- At the end it prints your **app URL** (`http://<server-ip>`) and the **teacher sign-up code**. Save both.

If your account uses a different region: `bash scripts/deploy.sh -var region=us-east-1`.

### Step 3: Open the app and create accounts
1. Open the app URL.
2. Register a **teacher**: choose "Teacher" and enter the sign-up code. To see the code again later: `terraform -chdir=infra output -raw teacher_signup_code`.
3. Register one or two **students** (use a different browser or a private window).
4. Mobile numbers must include the country code, for example `+919876543210`.

### Step 4: Try it
1. Teacher: create a class, add students by username, pick a date, mark everyone, save.
2. Student: sign in and check that you see only your own records.

### Step 5: Turn on the SMS reset code
New AWS accounts start in the SNS **SMS sandbox**: texts go only to phone numbers you have verified.
1. AWS Console, then **SNS**, then **Text messaging (SMS)**, then **Sandbox destination phone numbers**, then **Add phone number**. Enter the code AWS texts you.
2. Register in the app with that same number, then use "Forgot password?".

Delivering SMS to Indian numbers also requires registered sender details (DLT). If texts do not arrive, test with **log mode** instead:
```
bash scripts/deploy.sh -var otp_delivery=log
```
The code is then written to CloudWatch Logs (log group `/aws/lambda/attendance-dev-auth`) instead of being texted. Log mode is for testing only and is refused when the stage is `prod`. Switch back with `-var otp_delivery=sms`.

## Step-by-step alternative
The same thing as `deploy.sh`, one stage at a time:
```
bash scripts/build.sh                      # package the Lambda code
bash scripts/tf-init.sh                    # state bucket + terraform init
terraform -chdir=infra apply
bash scripts/deploy-frontend.sh            # build and publish the website
```

## Run the website on your own computer (development)
Useful while changing the frontend. It talks to the deployed API.
```
cd frontend
echo "VITE_API_URL=$(terraform -chdir=../infra output -raw api_url)" > .env
npm install
npm run dev
```
Open `http://localhost:5173`. This works because `dev_origins` in `infra/variables.tf` allows it. For a production setup, deploy with `-var 'dev_origins=[]'`.

## Run the automated tests
```
cd backend
pip install -r requirements-dev.txt
python -m pytest
```
The tests use a fake DynamoDB, so they need no AWS account.

## Making changes later

| You changed | Run |
|-------------|-----|
| Python code in `backend/` | `bash scripts/build.sh` then `terraform -chdir=infra apply` |
| React code in `frontend/` | `bash scripts/deploy-frontend.sh` |
| Anything in `infra/` | `terraform -chdir=infra apply` |

With CI/CD set up (next section), you do not need these: push to `main` and it deploys itself.

For error emails, deploy with `-var alert_email=you@example.com` and click the confirmation link AWS emails you.

## Automatic deployment (CI/CD)

Once set up, **every change pushed to the `main` branch is tested and deployed automatically**. No stored AWS keys are used: GitHub proves its identity to AWS with a short-lived token (OIDC), and AWS accepts it only for your repository and the `main` branch.

```
Developer opens a pull request --> CI runs: backend tests, frontend build, Terraform check
        |
   Merge to main --> Deploy workflow: tests again --> package code --> terraform apply
                     --> build website --> upload to S3 --> copy onto the EC2 web server
```

Workflows live in `.github/workflows/`: `ci.yml` (checks) and `deploy.yml` (deploy).

### One-time setup
1. **Put the project on GitHub.** Create an empty repository, then in the project folder:
   ```
   git init && git add . && git commit -m "First commit"
   git branch -M main
   git remote add origin https://github.com/YOUR-NAME/attendance-system.git
   git push -u origin main
   ```
2. **Tell Terraform which repository may deploy.** Copy the example file and edit the repository name:
   ```
   cp infra/terraform.tfvars.example infra/terraform.tfvars
   ```
   Set `github_repo = "YOUR-NAME/attendance-system"` and commit the file (it holds no secrets).
3. **Deploy once from your computer** so the AWS role and shared state bucket exist:
   ```
   bash scripts/deploy.sh
   ```
   If your AWS account already has a GitHub OIDC provider, add `create_github_oidc_provider = false` to `terraform.tfvars` first.
4. **Copy the role address:** `terraform -chdir=infra output -raw github_deploy_role_arn`
5. **Add two GitHub variables:** repository, then Settings, Secrets and variables, Actions, **Variables** tab, New repository variable:
   - `AWS_ROLE_ARN` = the address from step 4
   - `AWS_REGION` = `ap-south-1` (or your state region)
6. **Push any change to `main`** and watch the **Actions** tab. The app updates when the Deploy workflow turns green.

### Daily workflow for developers
1. Create a branch, make the change, open a pull request. CI checks it.
2. Merge the pull request. The app deploys itself in a few minutes.
3. To undo a bad release, revert the commit on `main`. The revert deploys automatically.

### Recommended protection
In GitHub, Settings, Branches, add a rule for `main`: require a pull request and require the **CI** checks to pass. This keeps unreviewed or failing code from reaching production.

### Good to know
- Terraform's state is now kept in a private S3 bucket `attendance-tfstate-<account-id>`, created by `scripts/tf-init.sh`. Deleting this project with `terraform destroy` does not delete it; remove it in the S3 console (Empty, then Delete).
- The deploy role has `AdministratorAccess` because Terraform manages IAM, Lambda, EC2 and more. Only the `main` branch of your repository can use it. Tighten it later if needed.
- The teacher sign-up code is never printed in CI logs. Read it on your computer with `terraform -chdir=infra output -raw teacher_signup_code`.
- Only one deployment runs at a time; extra pushes wait in line.

## API reference

| Method and path | Who | Purpose |
|-----------------|-----|---------|
| `GET /health` | anyone | Check the API is up |
| `POST /auth/register` | anyone | Create an account |
| `POST /auth/login` | anyone | Sign in with email or username |
| `POST /auth/forgot` | anyone | Text a reset code to a registered number |
| `POST /auth/reset` | anyone | Set a new password using the code |
| `POST /classes`, `GET /classes` | teacher | Create / list own classes |
| `POST /classes/{id}/students`, `GET /classes/{id}/students` | teacher | Add by username / list class students |
| `POST /attendance` | teacher | Save attendance for a class and date |
| `GET /attendance?classId=&date=` | teacher | View a class on a day |
| `GET /attendance/me` | student | View own attendance |

## Security notes
- Passwords are hashed (scrypt); the OTP is stored only as a keyed hash, works once, expires in 5 minutes, and locks after 5 wrong tries.
- Login locks for 15 minutes after 5 wrong passwords. The same message is shown for unknown users and wrong passwords.
- The web server has **no SSH port open**; files are delivered through S3 and AWS Systems Manager. It requires IMDSv2, has an encrypted disk, and nginx sends standard security headers (including a Content Security Policy). The S3 bucket is private.
- **The website uses HTTP, not HTTPS**, because HTTPS needs a domain name. Anyone on the same network could read passwords as they are sent. This is acceptable for a demo; for real use, buy a domain, point it at the server's IP, and add a free Let's Encrypt certificate (for example with Caddy or certbot), then change the API's allowed origin to `https://your-domain`.
- Each Lambda has only the database permissions it needs.
- The API is rate limited (10 requests per second, burst 20).
- Known limits: the login token lives in the browser's local storage and stays valid for 8 hours even after a password reset. For a bigger deployment, consider httpOnly cookies, shorter tokens with refresh, and AWS WAF.
- Never commit `terraform.tfstate`; it contains secrets. It is already in `.gitignore`. For a team, move the state to an S3 backend.

## Cost
The design uses services with free tiers: DynamoDB provisioned capacity stays under the always-free 25 units, and Lambda and API Gateway have free allowances. The EC2 server is the one always-running part: use an instance type your console marks as **Free tier eligible** (`t3.micro` by default, or `-var instance_type=t2.micro`). AWS also charges a small hourly fee for public IPv4 addresses, which the free tier may or may not cover on your account. Free tier terms depend on your account type and date, so check the Billing console and keep the budget alert on. SMS texts are not free; the spend limit in `infra/sns.tf` caps them at 1 USD per month.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Unable to locate credentials` | Run `aws configure` |
| `InvalidParameterCombination` or "not eligible for Free Tier" for the instance | Use the type your region allows: `bash scripts/deploy.sh -var instance_type=t2.micro` |
| Opening the URL shows nothing / times out | Wait 2 to 3 minutes after the first deploy. Check the instance is running in EC2 and that you used `http://` (not `https://`) |
| `The server did not become ready` | Wait a few minutes and run `bash scripts/deploy-frontend.sh` again. The server needs internet access to register with SSM |
| `No default VPC` | Create one: `aws ec2 create-default-vpc`, then deploy again |
| App opens but shows a network or CORS error | Re-run `bash scripts/deploy.sh`; make sure you opened the server URL printed by the deploy (or `localhost:5173`) |
| Old version shows after a frontend change | Run `bash scripts/deploy-frontend.sh` and hard refresh (Ctrl+Shift+R) |
| No SMS arrives | Verify the number in the SNS sandbox, or use log mode (Step 5) |
| "That email/username/phone is already registered" | Each must be unique across users |
| `Permission denied` running a script | Run it as `bash scripts/<name>.sh` |
| Deploy workflow: `Not authorized to perform sts:AssumeRoleWithWebIdentity` | Check the `AWS_ROLE_ARN` variable, that `github_repo` in `terraform.tfvars` matches your repository exactly, and that you pushed to `main` |
| `EntityAlreadyExists` for the OIDC provider | Add `create_github_oidc_provider = false` to `terraform.tfvars` and apply again |
| Teacher code lost | `terraform -chdir=infra output -raw teacher_signup_code` |

## Delete everything
```
terraform -chdir=infra destroy
```
Type `yes`. This removes all AWS resources and data created by this project.
