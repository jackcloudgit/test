# Pre-commit Configuration & Terraform Version Validator

## Overview

This pre-commit configuration enforces **Terraform module version consistency** across your infrastructure code. It validates that all module sources in your `.tf` files use compatible version constraints and prevents configuration drift through version mismatches.

**Configuration File:** `.pre-commit-config.yaml`  
**Validator Script:** `pre-commit/scripts/terraform-version-validator.sh`  
**Trigger:** Git pre-commit hook (runs before each commit)  
**Scope:** All `*.tf` files in the repository

---

## What is Pre-commit?

**Pre-commit** is a framework that manages and maintains multi-language pre-commit hooks. It:

- Runs automated checks **before** code is committed to Git
- Prevents code with issues from being committed
- Supports custom scripts and multiple repository hooks
- Works with any Git repository
- Runs only on files that are staged for commit

**Official Site:** https://pre-commit.com/

---

## Installation

### Prerequisites

- **Python 3.8+** installed on your system
- **Git** installed and initialized in the project
- **Bash shell** — macOS/Linux (native), Windows: Git Bash or WSL required to execute the `.sh` validator script

### Step 1: Install Pre-commit Framework

```bash
# Using pip (recommended)
pip install pre-commit

# Or using Homebrew (macOS)
brew install pre-commit

# Verify installation
pre-commit --version
```

### Step 2: Clone/Navigate to Repository

```bash
cd /path/to/your/terraform-repo
git clone <repo-url>
cd <repo-name>
```

### Step 3: Install Git Hooks

From the repository root, run:

```bash
pre-commit install
```

**What this does:**
- Creates `.git/hooks/pre-commit` script
- Registers pre-commit framework to run on every `git commit`
- Hooks are installed locally (per repository)

**Output:**
```
pre-commit installed at .git/hooks/pre-commit
```

### Step 4: Verify Installation

```bash
ls -la .git/hooks/pre-commit
```

Should show the pre-commit hook file exists.

---

### Configuration Structure

```yaml
repos:
  - repo: local                          # Local repository (custom scripts)
    hooks:
      - id: terraform-version-validator  # Unique hook ID
        name: Terraform Version Constraint Validator  # Display name
        entry: ./pre-commit/scripts/terraform-version-validator.sh  # Script path
        language: script                 # Execution language
        files: \.tf$                    # File pattern to match (regex)
        pass_filenames: false           # Don't pass file names as arguments
```

### Configuration Explanation

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `repo` | `local` | Hook source is a local script (not external repo) |
| `id` | `terraform-version-validator` | Unique identifier for this hook |
| `name` | `Terraform Version Constraint Validator` | Human-readable hook name (shown in output) |
| `entry` | `./pre-commit/scripts/terraform-version-validator.sh` | Script to execute |
| `language` | `script` | Execute as a shell script |
| `files` | `\.tf$` | Only run on files ending with `.tf` |
| `pass_filenames` | `false` | Don't pass staged filenames to script (script finds files itself) |

---

## The Terraform Version Validator

### Purpose

The `terraform-version-validator.sh` script validates two critical rules:

1. **All registry modules must have version constraints** — Prevents using unversioned modules from Terraform Registry
2. **Version constraints must be consistent** — Prevents the same module source from being pinned to different versions in the same repository

### How It Works

#### Step 1: Discover Terraform Files
- Searches for all `*.tf` files in the repository
- Excludes `.terraform/` directory (local modules cache)
- Processes files in sorted order

#### Step 2: Parse Module Declarations
For each file, the script extracts:
- Module name (e.g., `my_module`)
- Module source (e.g., `app.terraform.io/Organization/module/provider`)
- Version constraint (e.g., `>= 6.0.0`, `~> 7.0`)

**Example parsed module:**
```terraform
module "gke_cluster" {
  source  = "app.terraform.io/Organization/dnb_gcp_private_gke/google"
  version = ">= 7.0.0"
}
```

**Extracted values:**
- Module name: `gke_cluster`
- Source: `app.terraform.io/Organization/dnb_gcp_private_gke/google`
- Version: `>= 7.0.0`

#### Step 3: Classify Module Sources

**Registry Sources** (require version constraint):
- `app.terraform.io/Organization/module/provider`
- `registry.terraform.io/namespace/module/provider`
- Any non-local, non-remote reference

**Local/Remote Sources** (version constraint optional):
- `./local/path`
- `../relative/path`
- `git::https://...`
- `s3:://bucket/path`
- `https://...` (remote URLs)

#### Step 4: Validate Constraints

**Check 1: Missing Version for Registry Modules**
```
ERROR: Terraform registry module has no version constraint.
  Source: app.terraform.io/Organization/my_module/google
  Occurrences:
    - main.tf :: module "cluster"
```

**Check 2: Inconsistent Constraints for Same Source**
```
ERROR: Incompatible version constraints detected for the same module source.
  Source: app.terraform.io/Organization/my_module/google
  Constraints found:
    - >= 6.0.0
    - ~> 7.0.0
  Occurrences:
    - module1.tf :: module "cluster1"
    - module2.tf :: module "cluster2"
```

#### Step 5: Exit Code
- **Exit 0**: All validations passed ✅
- **Exit 1**: One or more validations failed ❌

---

## Usage & Workflow

### Automatic Execution (Standard Workflow)

#### 1. **Create or Modify Terraform Files**
```bash
# Edit your Terraform configuration
cat > main.tf << 'EOF'
module "vpc" {
  source = "app.terraform.io/MyOrg/vpc/aws"
  # Missing version constraint!
}
EOF
```

#### 2. **Stage Changes**
```bash
git add main.tf
```

#### 3. **Commit Changes**
```bash
git commit -m "Add VPC module"
```

**Pre-commit will automatically run:**
```
[INFO] Initializing environment for .
[terraform-version-validator] Terraform Version Constraint Validator
ERROR: Terraform registry module has no version constraint.
  Source: app.terraform.io/MyOrg/vpc/aws
  Occurrences:
    - main.tf :: module "vpc"

Terraform version constraint validation failed with 1 issue(s).
```

**Commit is rejected.** ❌ You must fix the error.

#### 4. **Fix the Issues**
```terraform
module "vpc" {
  source  = "app.terraform.io/MyOrg/vpc/aws"
  version = ">= 3.0.0"  # Add version constraint
}
```

#### 5. **Stage and Commit Again**
```bash
git add main.tf
git commit -m "Add VPC module with version constraint"
```

**Pre-commit runs and passes:**
```
[INFO] Initializing environment for .
[terraform-version-validator] Terraform Version Constraint Validator
Terraform version constraint validation passed.
```

**Commit succeeds.** ✅

---

### Manual Execution

Run the validator without committing:

```bash
# Run validator on all .tf files
pre-commit run terraform-version-validator --all-files

# Run on staged files only
pre-commit run terraform-version-validator

# Run all hooks
pre-commit run --all-files
```

---

## Validation Rules & Examples

### Rule 1: Registry Modules Must Have Version Constraints

#### ❌ FAIL: No Version Constraint
```terraform
module "gke" {
  source = "app.terraform.io/Organization/dnb_gcp_private_gke/google"
  # Missing version!
}
```

**Error:**
```
ERROR: Terraform registry module has no version constraint.
  Source: app.terraform.io/Organization/dnb_gcp_private_gke/google
  Occurrences:
    - main.tf :: module "gke"
```

#### ✅ PASS: Version Constraint Present
```terraform
module "gke" {
  source  = "app.terraform.io/Organization/dnb_gcp_private_gke/google"
  version = ">= 7.0.0"  # ✅ Constraint provided
}
```

---

### Rule 2: Same Module Source Must Have Same Version Constraints

#### ❌ FAIL: Inconsistent Versions
```terraform
# In cluster1.tf
module "gke_prod" {
  source  = "app.terraform.io/Organization/dnb_gcp_private_gke/google"
  version = ">= 7.0.0"
}

# In cluster2.tf
module "gke_staging" {
  source  = "app.terraform.io/Organization/dnb_gcp_private_gke/google"
  version = "~> 6.0"  # Different constraint!
}
```

**Error:**
```
ERROR: Incompatible version constraints detected for the same module source.
  Source: app.terraform.io/Organization/dnb_gcp_private_gke/google
  Constraints found:
    - >= 7.0.0
    - ~> 6.0
  Occurrences:
    - cluster1.tf :: module "gke_prod"
    - cluster2.tf :: module "gke_staging"
```

#### ✅ PASS: Consistent Versions
```terraform
# In cluster1.tf
module "gke_prod" {
  source  = "app.terraform.io/Organization/dnb_gcp_private_gke/google"
  version = ">= 7.0.0"  # ✅ Same constraint
}

# In cluster2.tf
module "gke_staging" {
  source  = "app.terraform.io/Organization/dnb_gcp_private_gke/google"
  version = ">= 7.0.0"  # ✅ Same constraint
}
```

---

### Rule 3: Local/Remote Sources Are Optional

#### ✅ PASS: Local Module (No Version Needed)
```terraform
module "custom" {
  source = "./modules/custom-module"
  # No version constraint required for local modules
}
```

#### ✅ PASS: Remote Git Source (No Version Needed)
```terraform
module "remote" {
  source = "git::https://github.com/myorg/terraform-modules.git?ref=main"
  # No version constraint needed for git sources
}
```

---

## Checks Performed

### Check 1: Missing Version Constraint for Registry Modules

**What it checks:**
- Module source is from Terraform Registry (e.g., `app.terraform.io/...`, `registry.terraform.io/...`)
- No `version` attribute is specified

**Why it matters:**
- Unversioned modules can change unexpectedly
- Leads to non-reproducible infrastructure
- Violates IaC best practices

**How to fix:**
```terraform
# Before: ❌
module "vpc" {
  source = "app.terraform.io/MyOrg/vpc/aws"
}

# After: ✅
module "vpc" {
  source  = "app.terraform.io/MyOrg/vpc/aws"
  version = ">= 3.0.0"  # Add this line
}
```

---

### Check 2: Inconsistent Version Constraints for Same Module

**What it checks:**
- Same module source appears multiple times in the repository
- Different version constraints are used for the same source

**Why it matters:**
- Causes inconsistent behavior across infrastructure
- Can create compatibility issues
- Makes debugging difficult

**How to fix:**
```terraform
# Problem: Same module, different versions across files

# File A: ❌
module "gke1" {
  source  = "app.terraform.io/Org/dnb_gcp_private_gke/google"
  version = ">= 7.0.0"
}

# File B: ❌
module "gke2" {
  source  = "app.terraform.io/Org/dnb_gcp_private_gke/google"
  version = "~> 6.0"
}

# Solution: Use same version in both files

# File A: ✅
module "gke1" {
  source  = "app.terraform.io/Org/dnb_gcp_private_gke/google"
  version = ">= 7.0.0"
}

# File B: ✅
module "gke2" {
  source  = "app.terraform.io/Org/dnb_gcp_private_gke/google"
  version = ">= 7.0.0"  # Changed to match
}
```

---

## Troubleshooting

### Issue 1: "Command 'pre-commit' not found"

**Problem:** Pre-commit is installed via pip but the executable is not on PATH (common on Windows with user-scoped installs).

**Solution:**
```bash
# Option A: use the module form — works without any PATH changes
python -m pre_commit install
python -m pre_commit run --all-files

# Option B: confirm it is actually installed
pip install pre-commit
python -m pre_commit --version
```

---

### Issue 2: Hooks Not Running on Commit

**Problem:** Pre-commit hooks are not executing.

**Solution:**
```bash
# Reinstall hooks
pre-commit install

# Verify installation
ls -la .git/hooks/pre-commit

# Test manually
pre-commit run --all-files
```

---

### Issue 3: "terraform-version-validator.sh: Permission Denied"

**Problem:** Script doesn't have execute permission.

**Solution:**
```bash
chmod +x pre-commit/scripts/terraform-version-validator.sh
```

---

### Issue 4: Validation Fails Unexpectedly

**Problem:** Script finds errors you don't expect.

**Solution:**
```bash
# Run the validator manually to see all errors
pre-commit run terraform-version-validator --all-files

# Run with debug output
bash -x pre-commit/scripts/terraform-version-validator.sh
```

---

### Issue 5: "git failed. Is it installed, and are you in a Git repository directory?"

**Problem:** `pre-commit install` was run in a folder that is not a Git repository (no `.git` directory present).

**Solution:**
```bash
# Check whether the current folder is a Git repo
git rev-parse --show-toplevel

# If it is not initialised, initialise it first
git init
pre-commit install

# If the folder is a subfolder of a repo, cd to the repo root first
cd /path/to/repo-root
pre-commit install
```

---

### Issue 6: "Commit Blocked but I Want to Force Push"

**Problem:** Pre-commit validation is blocking a necessary commit.

**Solution (Use with caution):**
```bash
# Bypass pre-commit hooks for a single commit
git commit --no-verify -m "Your commit message"

# ⚠️ WARNING: Only use when absolutely necessary
# You still need to fix the issues before merging to main
```

---

## Best Practices

### 1. **Consistent Version Constraints Across Repository**
Always use the same version constraint for the same module across your entire repository.

```terraform
# ✅ Good: Consistent version across all environments
module "vpc_prod" {
  source  = "app.terraform.io/MyOrg/vpc/aws"
  version = ">= 3.0.0, < 4.0.0"
}

module "vpc_staging" {
  source  = "app.terraform.io/MyOrg/vpc/aws"
  version = ">= 3.0.0, < 4.0.0"  # Same constraint
}
```

### 2. **Use Semantic Versioning Operators**

| Operator | Meaning | Example | Allows |
|----------|---------|---------|--------|
| `=` | Exact version | `= 3.5.0` | Only 3.5.0 |
| `!=` | Exclude version | `!= 2.0.0` | Any except 2.0.0 |
| `>`, `>=` | Greater than | `>= 3.0.0` | 3.0.0 and higher |
| `<`, `<=` | Less than | `<= 4.0.0` | 4.0.0 and lower |
| `~>` | Pessimistic | `~> 3.5` | 3.5+, <4.0 |

```terraform
# ✅ Recommended: Flexible but safe
version = ">= 7.0.0, < 8.0.0"

# ✅ Also good: Pessimistic version
version = "~> 7.0"

# ❌ Avoid: Too strict (blocks updates)
version = "= 7.0.0"

# ❌ Avoid: Too loose (unpredictable)
version = ">= 1.0.0"
```

### 3. **Review Pre-commit Output**

Always read validation output carefully:

```bash
# ✅ Good practice
pre-commit run --all-files
# Review output before committing
git add .
git commit -m "Your message"
```

### 4. **Update Module Versions Intentionally**

When updating a module version:

1. Test changes in a branch
2. Update version constraint
3. Update **all** instances of that module
4. Run pre-commit to validate
5. Commit with descriptive message

```bash
git checkout -b feature/upgrade-gke-module
# Edit all references to the module
vim module1.tf module2.tf
git add module1.tf module2.tf
pre-commit run --all-files  # Validate consistency
git commit -m "Upgrade dnb_gcp_private_gke from ~7.0 to ~8.0"
```

### 5. **Document Version Choices**

Add comments explaining why you chose a specific version:

```terraform
module "gke" {
  # Pin to 7.x because 8.x requires changes in our VPC configuration
  # TODO: Upgrade to 8.0+ when VPC refactor is complete (JIRA-123)
  source  = "app.terraform.io/Organization/dnb_gcp_private_gke/google"
  version = ">= 7.0.0, < 8.0.0"
}
```

---

## Common Version Constraint Patterns

### Pattern 1: Allow Patch Updates Only
```terraform
# Allows: 7.0.1, 7.0.2, 7.1.0 (same major.minor)
version = "~> 7.0"
```

### Pattern 2: Allow Minor & Patch Updates
```terraform
# Allows: 7.1.0, 7.2.0, 7.9.9 (same major)
version = "~> 7"
```

### Pattern 3: Allow Only Specific Major Version
```terraform
# Allows: 7.0.0 through 7.9.9
version = ">= 7.0.0, < 8.0.0"
```

### Pattern 4: Require Minimum Version
```terraform
# Allows: 7.0.0 and any higher version
version = ">= 7.0.0"
```

---