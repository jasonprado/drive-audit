#!/usr/bin/env python3
"""Audits Google Drive folder contents to identify dangerous permissions.
"""

import collections
import io
import os
import time
from oauth2client.service_account import ServiceAccountCredentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import gspread
import pandas as pd
from pprint import pprint
from ratelimit import limits, sleep_and_retry
from gspread_formatting import ConditionalFormatRule, BooleanRule, BooleanCondition, GridRange, CellFormat, Color, get_conditional_format_rules


SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/spreadsheets']


def run(spreadsheet_id, google_credential_path):
  google_credentials = ServiceAccountCredentials.from_json_keyfile_name(
    google_credential_path, scopes=SCOPES)

  gauth = GoogleAuth()
  gauth.credentials = google_credentials
  gauth.ServiceAuth()
  drive = GoogleDrive(gauth)
  gspread_service = gspread.service_account(filename=google_credential_path)
  sheet = gspread_service.open_by_key(spreadsheet_id)

  print("Fetching existing spreadsheet")
  existing_inventory = get_existing_inventory(sheet.sheet1)

  all_files = get_all_files(drive)

  existing_inventory = existing_inventory[["id", "approvedForOpenAccess"]]
  merged = pd.merge(
    all_files,
    existing_inventory,
    on='id',
    how='left',
  )

  # Write it back out
  merged.fillna('', inplace=True)
  merged = merged[["title", "anyoneWithLinkRole", "approvedForOpenAccess", "ownerEmail", "alternateLink", "id"]]
  print(merged)
  sheet.sheet1.update([merged.columns.values.tolist()] + merged.values.tolist())

  # Add highlight for violations
  purple_folder_rule = ConditionalFormatRule(
      ranges=[GridRange.from_a1_range('A2:F' + str(len(merged) + 1), sheet.sheet1)],
      booleanRule=BooleanRule(
          condition=BooleanCondition('CUSTOM_FORMULA', ['=AND(REGEXMATCH($E2, "/folders"), NOT(LEN($B2)=0),NOT($C2))']),
          format=CellFormat(backgroundColor=Color(2/3.,0,1))
      )
  )
  red_file_rule = ConditionalFormatRule(
      ranges=[GridRange.from_a1_range('A2:F' + str(len(merged) + 1), sheet.sheet1)],
      booleanRule=BooleanRule(
          condition=BooleanCondition('CUSTOM_FORMULA', ['=AND(NOT(LEN($B2)=0),NOT($C2))']),
          format=CellFormat(backgroundColor=Color(1,0,0))
      )
  )
  rules = get_conditional_format_rules(sheet.sheet1)
  rules.clear()
  rules.append(purple_folder_rule)
  rules.append(red_file_rule)
  rules.save()

  # Add checkbox for approvedForOpenAccess
  requests = {"requests": [
    {
        "repeatCell": {
            "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}},
            "range": {"sheetId": sheet.sheet1.id, "startRowIndex": 1, "endRowIndex":len(merged) + 1, "startColumnIndex": 2, "endColumnIndex": 3},
            "fields": "dataValidation"
        }
    }
  ]}
  sheet.batch_update(requests)


def get_all_files(drive):
  all_files = None
  for file_list in drive.ListFile({'maxResults': 100}):
    print('Received {} files from Files.list()'.format(len(file_list)))
    for file1 in file_list:
      do_google_api_call(lambda: file1.GetPermissions())
      file1['anyoneWithLinkRole'] = ([perm.get('role', '') for perm in file1.get('permissions', []) if perm.get('id') == 'anyoneWithLink'] or [''])[0]
      file1['ownerEmail'] = file1['owners'][0]['emailAddress']
      pprint(file1)
    df = pd.DataFrame.from_records(file_list)
    df["anyoneWithLinkRole"] = df["anyoneWithLinkRole"].astype("category")
    if all_files is not None:
      all_files = all_files.append(df)
    else:
      all_files = df
    all_files = all_files[["id", "title", "anyoneWithLinkRole", "alternateLink", "ownerEmail"]]
    break

  return all_files


@sleep_and_retry
@limits(calls=400, period=100)  # Rule is 500 requests per 100 seconds per project, and we're conservative
def do_google_api_call(fn):
  fn()
  time.sleep(.001)


def get_existing_inventory(sheet):
  df = pd.DataFrame(sheet.get_all_records())
  default_false_map = collections.defaultdict(lambda: False)
  default_false_map.update({'TRUE': True, 'FALSE': False})
  df['approvedForOpenAccess'] = df['approvedForOpenAccess'].map(default_false_map)
  return df


def main():
  from dotenv import load_dotenv
  load_dotenv()
  run(
    spreadsheet_id=os.getenv('SPREADSHEET_ID'),
    google_credential_path=os.getenv('GOOGLE_CREDENTIAL_PATH'),
  )

if __name__ == '__main__':
  main()
