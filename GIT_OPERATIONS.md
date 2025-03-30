# Git Operations Guide for Smørås Fotball

This guide explains how to use the Git management tools provided in the Smørås Fotball project.

## Background

The Smørås Fotball project uses Git for version control and to manage database backups between different environments. When deploying to production, it's important to maintain proper Git configuration and database backups to ensure smooth transitions and data preservation.

## Available Tools

The project includes several Git management tools:

1. **`fix_git_issues.py`** - Fixes common Git configuration issues, creates database backups, and ensures proper pushing to the repository.
2. **`manage_git.py`** - A comprehensive Git management utility with options for specific operations.
3. **`git-manager.sh`** - A shell script wrapper around the Python Git utility for easier use.

## Common Git Operations

### Checking Repository Status

To check the current state of your Git repository:

```bash
./git-manager.sh status
```

This will show you:
- Current branch
- Unpushed commits
- Uncommitted changes
- Untracked files

### Creating a Database Backup

To create and commit a database backup:

```bash
./git-manager.sh backup -m "Added new players and updated team roster"
```

If you don't provide a commit message (`-m` option), a default message with the current timestamp will be used.

This operation:
1. Creates a JSON backup of the entire database
2. Updates the `deployment_db.json` file (used for deployment restoration)
3. Stages both files for commit
4. Commits the changes with your message

### Pushing Changes to GitHub

To push your local commits to the GitHub repository:

```bash
./git-manager.sh push
```

This will:
1. Check if you have unpushed commits
2. Pull with rebase to avoid conflicts
3. Push your changes to the remote repository

### Pulling Latest Changes

To get the latest changes from the GitHub repository:

```bash
./git-manager.sh pull
```

This will:
1. Stash any uncommitted changes
2. Pull the latest changes 
3. Restore your uncommitted changes (if any)

### Setting Up Git

If you need to reconfigure Git credentials or settings:

```bash
./git-manager.sh setup
```

This will:
1. Configure Git user information
2. Set up credential caching
3. Check for GitHub token availability

### Running All Operations

To create a backup, commit, push, and pull in one command:

```bash
./git-manager.sh all -m "Weekly database backup"
```

## Git Workflow for Deployments

When working with deployments, we recommend the following workflow:

1. Before making significant changes in development:
   ```bash
   ./git-manager.sh pull
   ```

2. After completing your development work:
   ```bash
   ./git-manager.sh backup -m "Describe your changes"
   ```

3. Push your changes to the repository:
   ```bash
   ./git-manager.sh push
   ```

4. In production, after redeployment:
   ```bash
   python auto_restore_after_deploy.py
   ```

## Troubleshooting

If you encounter Git issues (such as authentication failures or merge conflicts), try:

```bash
python fix_git_issues.py
```

This script will:
1. Properly configure Git
2. Create a fresh database backup
3. Push changes safely
4. Report any issues

## Git Credentials

For secure GitHub access, the system uses a GitHub token stored in the `GITHUB_TOKEN` environment variable. This token is configured in the Replit environment and should not be modified manually.

If you need to update the GitHub token, please contact a system administrator.

## Database Backups in Git

Database backups are stored in the `deployment/` directory with the following naming convention:
- `git_backup_YYYYMMDD_HHMMSS.json` - Individual timestamped backups
- `deployment_db.json` - The latest backup that will be used for deployment restoration

These files are automatically included in Git commits to ensure proper data preservation.