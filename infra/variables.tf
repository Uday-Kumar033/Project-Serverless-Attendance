variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "stage" {
  type    = string
  default = "dev"
}

variable "allowed_origin" {
  type        = string
  default     = "http://localhost:5173"
  description = "Frontend origin for CORS (use the CloudFront URL in prod)"
}
