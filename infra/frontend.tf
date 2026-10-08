# Hosting for the React app: one small EC2 server running nginx.
# Files reach the server through a private S3 bucket and AWS Systems Manager (SSM),
# so no SSH port is open and no key pair is needed.

resource "random_id" "bucket" {
  byte_length = 4
}

# ---------- Upload bucket (private) ----------
resource "aws_s3_bucket" "web" {
  bucket        = "attendance-${var.stage}-web-${random_id.bucket.hex}"
  force_destroy = true # lets `terraform destroy` delete the bucket even if it has files
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------- Network ----------
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

resource "aws_security_group" "web" {
  name        = "attendance-${var.stage}-web"
  description = "Public web traffic only (no SSH)"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------- Permissions for the server ----------
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "web" {
  name               = "attendance-${var.stage}-web"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

# Lets us run commands on the server without SSH.
resource "aws_iam_role_policy_attachment" "web_ssm" {
  role       = aws_iam_role.web.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Lets the server download the website files from the bucket.
data "aws_iam_policy_document" "web_s3" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.web.arn}/*"]
  }
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.web.arn]
  }
}

resource "aws_iam_role_policy" "web_s3" {
  name   = "read-website-files"
  role   = aws_iam_role.web.id
  policy = data.aws_iam_policy_document.web_s3.json
}

resource "aws_iam_instance_profile" "web" {
  name = "attendance-${var.stage}-web"
  role = aws_iam_role.web.name
}

# ---------- Server ----------
data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_instance" "web" {
  ami                         = data.aws_ssm_parameter.al2023_ami.value
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.web.id]
  iam_instance_profile        = aws_iam_instance_profile.web.name
  user_data                   = templatefile("${path.module}/user_data.sh.tftpl", { region = var.region })
  user_data_replace_on_change = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required" # IMDSv2 only
  }

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "attendance-${var.stage}-web" }
}

# A fixed public address that survives stop/start.
resource "aws_eip" "web" {
  domain   = "vpc"
  instance = aws_instance.web.id
}
