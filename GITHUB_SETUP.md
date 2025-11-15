# GitHub Setup Guide

Follow these steps to upload your Handbook project to GitHub.

## Step 1: Initialize Git (if not already done)

```bash
cd /home/lesli/Data/Handbook

# Initialize git repository
git init
git branch -M main  # Use 'main' instead of 'master'
```

## Step 2: Add and Commit Files

```bash
# Add all files (respects .gitignore)
git add .

# Check what will be committed
git status

# Create initial commit
git commit -m "Initial commit: UTS Handbook Chatbot project

- RAG pipeline for UTS course queries
- Qdrant vector database integration
- Ollama LLM backend
- FastAPI server
- Frontend chatbot widget
- Course data ingestion and embedding scripts"
```

## Step 3: Create GitHub Repository

1. Go to [https://github.com](https://github.com) and sign in
2. Click the **"+"** icon in the top right → **"New repository"**
3. Fill in:
   - **Repository name**: `uts-handbook-chatbot` (or your preferred name)
   - **Description**: "RAG chatbot for UTS course information"
   - **Visibility**: Choose Public or Private
   - **DO NOT** check:
     - ❌ Add a README file
     - ❌ Add .gitignore
     - ❌ Choose a license
   (We already have these files!)
4. Click **"Create repository"**

## Step 4: Connect and Push

After creating the repository, GitHub will show you commands. Use these:

```bash
# Add GitHub as remote (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/uts-handbook-chatbot.git

# Verify remote was added
git remote -v

# Push to GitHub
git push -u origin main
```

## Alternative: Using GitHub CLI

If you have GitHub CLI (`gh`) installed:

```bash
# Authenticate (first time only)
gh auth login

# Create repo and push in one command
gh repo create uts-handbook-chatbot --public --source=. --remote=origin --push
```

## Verify Upload

1. Go to your repository on GitHub
2. Check that all files are there
3. Verify `.gitignore` is working (large files like `*.npy`, `models/`, etc. should NOT be uploaded)

## What Gets Uploaded

✅ **Will be uploaded:**
- Source code (`src/`)
- Configuration files (`*.yml`, `requirements.txt`)
- Documentation (`README.md`)
- Course JSON files (`data/courses/*.json`)
- Scripts and utilities
- Frontend files (`test_chatbot.html`, `src/js/`, `src/css/`)

❌ **Will NOT be uploaded** (thanks to `.gitignore`):
- Python cache (`__pycache__/`, `*.pyc`)
- Environment files (`.env`, `venv/`)
- Model binaries (`models/*.bin`, `*.safetensors`)
- Embeddings (`*.npy`, `*.npz`)
- Processed data (`data/processed/`, `data/embeddings/`)
- Qdrant/Ollama data stores
- Logs (`logs/`)
- IDE files (`.vscode/`, `.idea/`)

## Future Updates

After the initial push, to update your repository:

```bash
git add .
git commit -m "Description of your changes"
git push
```

## Troubleshooting

### "Repository not found" error
- Check that the repository name and username are correct
- Verify you have push access to the repository

### "Authentication failed"
- Use a Personal Access Token instead of password
- Or set up SSH keys: `ssh-keygen -t ed25519 -C "your_email@example.com"`

### Large file warnings
- Check `.gitignore` is working: `git status` should not show large files
- If needed, remove accidentally added files: `git rm --cached large_file.npy`

