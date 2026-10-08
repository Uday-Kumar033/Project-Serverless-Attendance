variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "stage" {
  type    = string
  default = "dev"
}

variable "dev_origins" {
  type        = list(string)
  default     = ["http://localhost:5173"]
  description = "Extra websites allowed to call the API (for running the frontend on your computer). Use [] in production."
}

variable "alert_email" {
  type        = string
  default     = ""
  description = "Email address for error alerts. Leave empty to skip."
}

variable "otp_delivery" {
  type        = string
  default     = "sms"
  description = "sms = send real text messages. log = write the code to CloudWatch Logs (testing only, blocked when stage is prod)."

  validation {
    condition     = contains(["sms", "log"], var.otp_delivery)
    error_message = "otp_delivery must be \"sms\" or \"log\"."
  }
}

variable "github_repo" {
  type        = string
  default     = ""
  description = "GitHub repository allowed to deploy, like owner/repo. Leave empty to skip CI/CD setup."
}

variable "github_branch" {
  type        = string
  default     = "main"
  description = "Only pushes to this branch may deploy."
}

variable "create_github_oidc_provider" {
  type        = bool
  default     = true
  description = "Set to false if your AWS account already has a GitHub OIDC provider."
}

variable "instance_type" {
  type        = string
  default     = "t3.micro"
  description = "Size of the web server. Pick the one your AWS console marks as Free tier eligible (t3.micro or t2.micro, depending on region)."
}
