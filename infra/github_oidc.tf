# Lets GitHub Actions deploy to this AWS account WITHOUT any stored access keys.
# GitHub proves who it is with a short-lived token; AWS accepts it only for your repo and branch.
# Created only when github_repo is set.

locals {
  ci_enabled = var.github_repo != ""
}

resource "aws_iam_openid_connect_provider" "github" {
  count           = local.ci_enabled && var.create_github_oidc_provider ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1", "1c58a3a8518e8759bf075b76b750d4f2df264fcd"]
}

data "aws_iam_openid_connect_provider" "github" {
  count = local.ci_enabled && !var.create_github_oidc_provider ? 1 : 0
  url   = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "github_assume" {
  count = local.ci_enabled ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.create_github_oidc_provider ? aws_iam_openid_connect_provider.github[0].arn : data.aws_iam_openid_connect_provider.github[0].arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/${var.github_branch}"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  count              = local.ci_enabled ? 1 : 0
  name               = "attendance-${var.stage}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_assume[0].json
}

# Terraform creates IAM roles, Lambdas, EC2 and more, so this role needs wide permissions.
# It can only be used by pushes to the branch above. Tighten it later if you want least privilege.
resource "aws_iam_role_policy_attachment" "github_deploy" {
  count      = local.ci_enabled ? 1 : 0
  role       = aws_iam_role.github_deploy[0].name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
