#!/bin/bash
# Git Manager - A simple wrapper for the Python Git management utility

# Display usage
function show_usage {
  echo "Smørås Fotball Git Manager"
  echo "Usage: $0 [command]"
  echo ""
  echo "Commands:"
  echo "  status    - Show current Git repository status"
  echo "  backup    - Create a database backup and commit it"
  echo "  push      - Push local changes to the remote repository"
  echo "  pull      - Pull changes from the remote repository"
  echo "  setup     - Configure Git user and credentials"
  echo "  all       - Run backup, push, and pull operations"
  echo ""
  echo "Examples:"
  echo "  $0 status"
  echo "  $0 backup -m \"Updated player profiles\""
}

# Check if Python script exists
if [ ! -f "manage_git.py" ]; then
  echo "Error: manage_git.py not found"
  exit 1
fi

# Process arguments
if [ $# -eq 0 ]; then
  show_usage
  exit 0
fi

# Pass all arguments to the Python script
python manage_git.py "$@"