terraform {
  required_version = ">= 1.6"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 6.28" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
  # POC: estado local (no se versiona). Migrar a S3 con bloqueo antes del piloto.
}

provider "aws" {
  region  = var.region
  profile = var.perfil_aws
  default_tags {
    tags = { proyecto = "mp-poc", ambiente = var.ambiente, gestionado_por = "terraform" }
  }
}
