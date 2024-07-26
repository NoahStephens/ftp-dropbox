#!/bin/bash
# Starts app using service and runs setup if the has not

if [ -d ../venv ]; then
  echo "python venv not installed"
#   echo "running setup..."
#   exec bin/setup.sh
fi

source venv/bin/activate

# pip install -r requirements.txt

if [ -n "$ZSH_VERSION" ]; then
  echo "zsh: ${ZSH_VERSION}"
  PWD="$(cd "$(dirname "${0}")" && pwd)/.."
elif [ -n "$BASH_VERSION" ]; then
  echo "bash: ${BASH_VERSION}"
  PWD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
fi

# Build system control serice
PYTHONPATH=$PWD $PWD/venv/bin/python src/dropbox.py
deactivate