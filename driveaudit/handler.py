from .driveaudit import run
import dotenv
import logging

def handle(_):
  config = dotenv.dotenv_values("/var/openfaas/secrets/driveaudit-config.env")
  print("STARTING")
  run(
    spreadsheet_id=config['SPREADSHEET_ID'],
    google_credential_path=config['GOOGLE_CREDENTIAL_PATH'],
  )
  return '{"status":"ok"}'
