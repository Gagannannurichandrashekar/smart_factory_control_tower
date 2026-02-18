#!/bin/bash

# Script to push Smart Factory Control Tower to GitHub
# Before running: Create a repository at https://github.com/new
# Name it: smart-factory-control-tower

echo "🚀 Pushing Smart Factory Control Tower to GitHub"
echo "================================================"
echo ""

# Check if remote exists
if git remote get-url origin &>/dev/null; then
    echo "✅ Remote 'origin' already configured"
    git remote -v
else
    echo "❌ No remote configured"
    echo ""
    echo "Please provide your GitHub username:"
    read -p "GitHub Username: " GITHUB_USER
    
    if [ -z "$GITHUB_USER" ]; then
        echo "❌ Username required. Exiting."
        exit 1
    fi
    
    echo ""
    echo "Adding remote repository..."
    git remote add origin https://github.com/$GITHUB_USER/smart-factory-control-tower.git
    echo "✅ Remote added"
fi

echo ""
echo "Setting branch to 'main'..."
git branch -M main

echo ""
echo "Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully pushed to GitHub!"
    echo ""
    echo "📋 Next: Deploy to Streamlit Cloud"
    echo "   Go to: https://share.streamlit.io"
    echo "   Main file: app/Home.py"
else
    echo ""
    echo "❌ Push failed. Make sure:"
    echo "   1. Repository exists at: https://github.com/$GITHUB_USER/smart-factory-control-tower"
    echo "   2. You have push access"
    echo "   3. Repository is empty (or use --force if needed)"
fi

