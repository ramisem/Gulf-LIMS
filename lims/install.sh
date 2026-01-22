#!/bin/bash

SCRIPT1="./scripts/setup_env.sh"
SCRIPT2="./scripts/manual_file_modfification.sh"
SCRIPT3="./scripts/create_services.sh"

clear
while true; do
  echo "Please choose an option:"
  echo "1) Continue with Environment setup."
  echo "2) Continue with Config file modifications."
  echo "3) Continue with Service creation."
  echo "4) Exit"
  read -p "Enter your choice [1-4]: " choice

  case $choice in
  1)
    echo "Processing the script for Environment setup...."
    $SCRIPT1
    if [ $? -ne 0 ]; then
      echo "Script execution failed."
    else
      echo "Environment setup is successfully completed."
    fi
    ;;
  2)
    echo "Processing the script for Config file modifications..."
    $SCRIPT2
    if [ $? -ne 0 ]; then
      echo "script execution failed."
    else
      echo "Config file modifications are successfully completed."
    fi
    ;;
  3)
    echo "Processing the script for Service creation..."
    $SCRIPT3
    if [ $? -ne 0 ]; then
      echo "script execution failed."
    else
      echo "Service creation is successfully completed."
    fi
    ;;
  4)
    echo "Exiting..."
    break
    ;;
  *)
    echo "Invalid option. Please choose 1, 2, or 3."
    ;;
  esac
  # Prompt to ask if the user wants to continue
  read -p "Do you want to continue? (yes/no): " continue_choice
  case $continue_choice in
  [Yy]*)
    clear
    ;;
  [Nn]*)
    echo "Exiting..."
    break
    ;;
  *)
    echo "Invalid input. Exiting..."
    break
    ;;
  esac
done
