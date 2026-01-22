#!/bin/bash

SOURCE_APPLICATION_FOLDER="application"
TARGET_FOLDER="./target"
ZIP_FILE="gulf_lims.zip"
ZIP_APPLICATION_FILE="application.zip"
EXCLUDE_FOLDERS_FROM_APPLICATION_ZIP="*.git/*"

if [ ! -d "$TARGET_FOLDER" ]; then
  mkdir -p "$TARGET_FOLDER"
fi

rm $TARGET_FOLDER/$ZIP_FILE

if [ -d "$SOURCE_APPLICATION_FOLDER" ]; then
  # shellcheck disable=SC2164
  cd "$SOURCE_APPLICATION_FOLDER"
  zip -r "../$ZIP_APPLICATION_FILE" . -x "$EXCLUDE_FOLDERS_FROM_APPLICATION_ZIP"
  echo "Folder '$SOURCE_APPLICATION_FOLDER' has been zipped into './$ZIP_APPLICATION_FILE'."
  # shellcheck disable=SC2103
  cd ..
else
  echo "The folder '$SOURCE_APPLICATION_FOLDER' does not exist."
fi

zip -r "$TARGET_FOLDER/$ZIP_FILE" "imports" "scripts" "install.sh" "requirements.txt" "$ZIP_APPLICATION_FILE"
echo "Folder '$PWD' has been zipped into '$TARGET_FOLDER/$ZIP_FILE'."
rm $ZIP_APPLICATION_FILE
