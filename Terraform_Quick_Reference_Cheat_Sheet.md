# Terraform Quick Reference Cheat Sheet

**Stack:** Google Cloud, Terraform Cloud, private GitHub repositories.
**Purpose:** Standard command reference for troubleshooting and routine operations.

## 1. Standard Workflow Commands

```bash
terraform fmt -check -recursive
terraform init
terraform validate
terraform plan  -var-file=environments/nonprod.tfvars -out=tfplan
terraform apply tfplan
```

Each step must complete successfully before the next is executed.

## 2. State Management (Terraform Cloud Backend)

| Operation | Command |
|---|---|
| List resources in state | `terraform state list` |
| Show resource attributes | `terraform state show <address>` |
| Move or rename an address | `terraform state mv <old> <new>` |
| Remove from state (retain in GCP) | `terraform state rm <address>` |
| Import existing GCP resource | `terraform import <address> <gcp-id>` |
| Reinitialize after backend change | `terraform init -reconfigure` |
| Migrate state into TFC | `terraform init -migrate-state` |
| Force unlock (exception only) | `terraform force-unlock <LOCK_ID>` |

**Requirement:** Unlock through the Terraform Cloud UI first. `terraform force-unlock` may be executed only when the UI is unavailable and no active run exists.

## 3. Targeted Operations

| Scenario | Command | Requirement |
|---|---|---|
| Emergency-scope plan | `terraform plan -target=<address>` | Follow with a full untargeted plan |
| Emergency-scope apply | `terraform apply -target=<address>` | Document justification in the pull request |
| Standardize plan arguments | `TF_CLI_ARGS_plan` env variable | Configure on the Terraform Cloud workspace |

PowerShell:

```powershell
$env:TF_CLI_ARGS_plan="-refresh=true -compact-warnings -lock-timeout=300s"
```

Bash:

```bash
export TF_CLI_ARGS_plan="-refresh=true -compact-warnings -lock-timeout=300s"
```

## 4. Debugging

| Requirement | Action |
|---|---|
| Verbose logs (local) | `TF_LOG=DEBUG` and `TF_LOG_PATH=./terraform-debug.log` |
| Verbose logs (Terraform Cloud) | Set `TF_LOG=DEBUG` as a workspace environment variable, re-queue the run, then remove after investigation |
| Wrong working directory | `terraform -chdir=<path> <command>` |
| Configuration validation | `terraform validate` |
| GCP `403` error | Verify IAM bindings for the Terraform Cloud workspace service account |
| GCP `409 already exists` | Execute `terraform import` to reconcile state |

## 5. Environment Variables

Standard layout:

```text
environments/
  nonprod.tfvars
  prod.tfvars
  dr.tfvars
```

Required Terraform Cloud workspace configuration:

```
TF_CLI_ARGS_plan  = -var-file=environments/<env>.tfvars
TF_CLI_ARGS_apply = -var-file=environments/<env>.tfvars
```

Secrets must be stored as Terraform Cloud sensitive variables and must not be committed to source control.

## 6. Resource Replacement

| Operation | Command |
|---|---|
| Plan replacement | `terraform plan -replace=<address>` |
| Apply replacement | `terraform apply -replace=<address>` |
| Replacement via TFC UI | New run → Advanced options → Replace resources |

Replacement of stateful resources requires prior validation of backups and rehearsal in a non-production environment.

## 7. Module Updates

```bash
terraform init -upgrade
terraform plan -var-file=environments/nonprod.tfvars
```

Required steps:

- [ ] Review the module `CHANGELOG.md`
- [ ] Pin to a specific Git tag or Private Registry version
- [ ] Update the non-production consumer first
- [ ] Validate for a minimum of one business day before promoting to production
- [ ] Retain the previous version reference for rollback

## 8. Review Rejection Criteria

The following conditions must result in a pull request being rejected:

- Use of `-target` in a routine change without documented justification
- Unpinned module references (for example `ref=main` or omitted `version`)
- Persistent `TF_LOG=DEBUG` variables on a Terraform Cloud workspace
- Plan output containing undocumented resource destructions
- Secrets or credentials present in `.tf` or `.tfvars` files under source control

## 9. GCP-Specific Considerations

- Certain resources (for example `google_project_service`) reconcile asynchronously; subsequent plans may show transient diffs.
- Provider upgrades for `hashicorp/google` may introduce attribute renames; consult the provider upgrade guide before upgrading.
- Regional and global resource scopes must be verified when troubleshooting "not found" errors.

## 10. References

- Terraform CLI — https://developer.hashicorp.com/terraform/cli
- State documentation — https://developer.hashicorp.com/terraform/language/state
- `terraform state` — https://developer.hashicorp.com/terraform/cli/commands/state
- `terraform plan` — https://developer.hashicorp.com/terraform/cli/commands/plan
- Terraform Cloud documentation — https://developer.hashicorp.com/terraform/cloud-docs
- Google Cloud provider — https://registry.terraform.io/providers/hashicorp/google/latest/docs
