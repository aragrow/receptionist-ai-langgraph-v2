#!/bin/bash

# GitHub Incremental Branch Creator with Branch Summary
# Features:
# - Branch prefix defaults to current branch prefix
# - Asks for commit message (with sensible default)
# - Auto-detects GitHub repository
# - Warns if you're on a protected branch (main/master)
# - Increments branch number automatically
# - Creates branch first, then stages and commits changes directly on it
# - Generates branch-summary.md for LLM context restoration

set -e  # Exit on any error

# Configuration
DEFAULT_PREFIX="branch"
PROTECTED_BRANCHES=("main" "master")
SUMMARY_FILE="branch-summary.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print helpers
print_info()    { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error()   { echo -e "${RED}❌ $1${NC}"; }

# Check if inside git repo
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository!"
        exit 1
    fi
}

# Check if repo is GitHub
check_github_repo() {
    local remote_url
    remote_url=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ ! "$remote_url" =~ github\.com ]]; then
        print_error "This doesn't appear to be a GitHub repository!"
        print_info "Remote URL: $remote_url"
        exit 1
    fi
    print_success "GitHub repository detected: $remote_url"
}

# Warn if on protected branch
check_protected_branch() {
    local current_branch
    current_branch=$(git branch --show-current)
    for protected in "${PROTECTED_BRANCHES[@]}"; do
        if [[ "$current_branch" == "$protected" ]]; then
            print_warning "You are currently on the protected branch '$current_branch'!"
            read -p "Do you want to continue? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_info "Operation cancelled."
                exit 0
            fi
        fi
    done
}

# Extract prefix from current branch (if matches prefix-number pattern)
get_current_branch_prefix() {
    local current_branch
    current_branch=$(git branch --show-current)
    if [[ "$current_branch" =~ ^([a-zA-Z0-9_-]+)-[0-9]+$ ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo "$DEFAULT_PREFIX"
    fi
}

# Find next numeric branch for prefix
get_next_branch_number() {
    local prefix="$1"
    local highest=0
    local branches local_branches all_branches

    branches=$(git branch -r | grep -E "origin/${prefix}-[0-9]+$" | sed 's/.*origin\///' || true)
    local_branches=$(git branch | grep -E "${prefix}-[0-9]+$" | sed 's/^[* ]*//' || true)
    all_branches="$branches"$'\n'"$local_branches"

    while IFS= read -r branch; do
        if [[ "$branch" =~ ${prefix}-([0-9]+)$ ]]; then
            local num="${BASH_REMATCH[1]}"
            if (( num > highest )); then
                highest=$num
            fi
        fi
    done <<< "$all_branches"

    echo $((highest + 1))
}

# Create branch
create_branch() {
    local branch_name="$1"
    print_info "Creating new branch: $branch_name"
    git checkout -b "$branch_name"
    print_success "Switched to new branch: $branch_name"
}

# Generate branch summary for LLM context
generate_branch_summary() {
    local branch_name="$1"
    local commit_message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    print_info "Generating branch summary in $SUMMARY_FILE..."
    
    # Create header for this branch entry
    cat >> "$SUMMARY_FILE" << EOF

---
## Branch: $branch_name
**Created:** $timestamp  
**Commit Message:** $commit_message

### Files Changed:
\`\`\`
$(git diff --stat HEAD~1 HEAD 2>/dev/null || echo "No previous commit to compare")
\`\`\`

### Code Changes:
\`\`\`diff
$(git diff HEAD~1 HEAD 2>/dev/null || echo "No previous commit to compare")
\`\`\`

EOF
    
    print_success "Branch summary updated in $SUMMARY_FILE"
}

# Stage + commit changes with prompt
stage_and_commit() {
    local branch_name="$1"
    if git diff --quiet && git diff --cached --quiet; then
        print_info "No changes to stage and commit."
        return
    fi
    print_info "Staging all changes..."
    git add .
    if git diff --cached --quiet; then
        print_info "No staged changes to commit."
        return
    fi
    echo
    print_info "Enter commit message:"
    read -p "Commit message (default: 'Initial commit on $branch_name'): " commit_message
    commit_message=${commit_message:-"Initial commit on $branch_name"}

    # ⚡ Generate branch summary BEFORE commit
    branch_summary=$(generate_branch_summary "$branch_name" "$commit_message")

    git commit -m "$commit_message"
    print_success "Changes committed successfully with message: '$commit_message'"
    
}

# Push branch
push_branch() {
    local branch_name="$1"
    print_info "Pushing branch to remote..."
    git push -u origin "$branch_name"
    print_success "Branch pushed to GitHub successfully!"
}

# Initialize summary file if it doesn't exist
init_summary_file() {
    if [[ ! -f "$SUMMARY_FILE" ]]; then
        cat > "$SUMMARY_FILE" << EOF
# Branch Development Summary

This file tracks branch creation and changes for LLM context restoration.

**Repository:** $(git remote get-url origin 2>/dev/null || echo "Local repository")  
**Generated by:** GitHub Incremental Branch Creator  
**Last updated:** $(date '+%Y-%m-%d %H:%M:%S')

EOF
        print_info "Created new branch summary file: $SUMMARY_FILE"
    fi
}

# Main flow
main() {
    print_info "GitHub Incremental Branch Creator"
    echo

    # Initialize summary file
    init_summary_file

    # Get prefix from current branch
    current_prefix=$(get_current_branch_prefix)
    read -p "Enter branch prefix (default: $current_prefix): " prefix
    prefix=${prefix:-$current_prefix}

    check_git_repo
    check_github_repo
    check_protected_branch

    print_info "Fetching latest remote branches..."
    git fetch origin

    next_num=$(get_next_branch_number "$prefix")
    branch_name="${prefix}-${next_num}"
    print_info "Next branch will be: $branch_name"

    read -p "Create branch '$branch_name'? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "Operation cancelled."
        exit 0
    fi

    create_branch "$branch_name"
    stage_and_commit "$branch_name"
    push_branch "$branch_name"

    print_success "Branch '$branch_name' created and pushed successfully! 🎉"
    print_info "You are now on the new branch and ready to work!"
    print_info "Branch summary saved to: $SUMMARY_FILE"
}

main "$@"