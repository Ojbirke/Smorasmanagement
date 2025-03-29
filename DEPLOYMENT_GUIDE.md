# Smørås Fotball Deployment Guide

This guide explains how to deploy the Smørås Fotball application and maintain your data across deployments.

## Deployment Process

### First-Time Deployment

1. Make sure your code is ready for deployment
2. Click the "Deploy" button in Replit
3. Wait for the deployment process to complete
4. The app will be available at your Replit deployment URL

### After Making Changes in Production

If you've made important changes in your **production environment** (like adding teams, players, or matches) and want to make sure these changes are preserved during future deployments:

1. Run the following command in your production environment:
   ```
   python backup_production_data.py
   ```
   This will:
   - Create a backup of your current production database
   - Mark your environment as "production" so future deployments won't overwrite your data

2. You should see confirmation messages that the backup was successful

### Updating Code Without Losing Production Data

If you've previously marked your environment as production and want to deploy new code:

1. Make your code changes in the development environment
2. Click the "Deploy" button in Replit
3. The deployment process will:
   - Detect that this is a production environment
   - Preserve your existing database data
   - Apply only the code changes, not overwriting your production data

## Troubleshooting

### If Production Data is Overwritten

If your production data was accidentally overwritten during deployment:

1. Check if a safety backup was created by looking in the `deployment` folder for files named `pre_restore_safety_*.json` or `production_db_*.json`
2. If a backup exists, you can restore it with:
   ```
   python force_deployment_restore.py --backup=deployment/your_backup_file.json
   ```

### Manually Marking as Production

To manually mark your environment as production (if the Python script fails):

```
./mark_production.sh
```

This creates a marker file that tells the deployment process to preserve your data.

## Best Practices

1. **Always back up production data before deployment**
   Run `python backup_production_data.py` in production before deploying new code

2. **Test changes in development first**
   Make sure your changes work correctly in the development environment before deploying

3. **Check logs after deployment**
   After deploying, check the logs to ensure the process completed correctly

4. **Maintain regular backups**
   Periodically run `python backup_production_data.py` to create fresh backups of your production data