#!/bin/bash

# Script to push 1st Agent framework to GitHub and create a PR

echo "=========================================="
echo "  1st Agent Framework - GitHub Push Script"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "README.md" ]; then
    echo "ERROR: Not in the 1st agent directory"
    exit 1
fi

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "ERROR: Git repository not initialized"
    exit 1
fi

echo "✓ Git repository initialized"
echo ""

# Ask for GitHub repository URL
if [ -z "$GITHUB_REPO" ]; then
    read -p "Enter your GitHub repository URL (e.g., git@github.com:username/1st-agent.git): " GITHUB_REPO
fi

echo ""
echo "Repository URL: $GITHUB_REPO"
echo ""

# Ask for branch name
if [ -z "$BRANCH_NAME" ]; then
    read -p "Enter branch name for PR (e.g., feat/auto-mode): " BRANCH_NAME
fi

echo ""
echo "Branch name: $BRANCH_NAME"
echo ""

# Add remote
if ! git remote | grep -q origin; then
    git remote add origin "$GITHUB_REPO"
    echo "✓ Added remote: origin"
fi

echo ""

# Push to GitHub
echo "Pushing to GitHub..."
echo ""

git push -u origin master

if [ $? -eq 0 ]; then
    echo "✓ Successfully pushed to master"
    echo ""
    
    # Create and checkout new branch
    git checkout -b "$BRANCH_NAME"
    echo "✓ Created branch: $BRANCH_NAME"
    echo ""
    
    # Push the new branch
    git push -u origin "$BRANCH_NAME"
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully pushed branch: $BRANCH_NAME"
        echo ""
        echo "=========================================="
        echo "  NEXT STEPS:"
        echo "=========================================="
        echo ""
        echo "1. Go to: https://github.com/${GITHUB_REPO#*github.com/}/pulls"
        echo "2. Click 'New Pull Request'"
        echo "3. Set base branch to 'master'"
        echo "4. Set compare branch to '$BRANCH_NAME'"
        echo "5. Click 'Create Pull Request'"
        echo ""
        echo "Or use the GitHub CLI:"
        echo "  gh pr create --base master --head $BRANCH_NAME --title 'feat: Add AUTO mode and Continuous Goal Execution Loop' --body 'See commit message'"
        echo ""
    else
        echo "✗ Failed to push branch"
        exit 1
    fi
else
    echo "✗ Failed to push to master"
    exit 1
fi

echo "=========================================="
echo "  Script completed successfully!"
echo "=========================================="
