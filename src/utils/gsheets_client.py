"""Script to automate insertion of values in Google Sheets.

Google Sheets API credentials are required that can be obtained at
https://console.developers.google.com/flows/enableapi?apiid=sheets.googleapis.com

Example usage:
    client = GoogleSheetsClient('https://docs.google.com/spreadsheets/d/.../edit#gid=0',
            './client_secret.json')
    client.set_cell_value('Column name', 'Row name', 'New value')
    set_value = client.get_cell_value_formatted('Column name', 'Row name')
"""

import httplib2, os, re
from consts import GOOGLE_SHEETS_SHEET_NAME
from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage


SHEET_NAME = GOOGLE_SHEETS_SHEET_NAME
SHEET_RANGE = SHEET_NAME + '!A1:ZZ100000'
APPLICATION_NAME = 'Google Sheets Master'
DISCOVERY_URL = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_CREDENTIALS_FILE = 'google-sheets-master.json'
flags = None


def __init_args():
    global flags
    try:
        import argparse
        flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
    except ImportError:
        flags = None


class GoogleSheetsClient:

    def __init__(self, sheets_url, path_to_client_secret):
        """Args:
            :param sheets_url:            (str): URL of the Google Sheet to be processed.
            :param path_to_client_secret: (str): path to client credentials json file, relative or absolute

        If no credentials are found or they are invalid user is prompted for authentication
        to to obtain the new credentials.
        """
        try:
            path_to_client_secret = self.__get_absolute_path(path_to_client_secret)
            self.__spreadsheet_id = re.search('docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]*)/', sheets_url).group(1)
        except AttributeError:
            raise ValueError('Invalid url. Doesn\'t look like a valid Google Sheets link.')
        except IOError:
            print('Client secret path invalid!')
            raise

        http = self.__get_credentials(path_to_client_secret).authorize(httplib2.Http())
        self.__service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=DISCOVERY_URL)


    def set_cell_value(self, column_name, row_name, value, silent_mode=True):
        """Inserts value in a Google Sheet. 

            Args:
                :param column_name: (str):  Column name.
                :param row_name:    (str):  Row name.
                :param value:       (str):  Value to be inserted.
                :param silent_mode: (bool): Whether log messages should be printed.

            Returns:
                (bool): The return value. True for success, False otherwise.
        """
        service = self.__service
        spreadsheet_id = self.__spreadsheet_id
        cell_index = self.get_cell_index_formatted(column_name, row_name)
        request_body = {'values': [[value]]}

        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=cell_index,
            valueInputOption='USER_ENTERED', body=request_body).execute()

        if result.get('updatedCells') == 1:
            if not silent_mode:
                print('Cell ', cell_index, 'updated with value ', value)
            return True
        else:
            if not silent_mode:
                print('Operation failed')
            return False


    def get_cell_value(self, column_name, row_name):
        """Gets value from a Google Sheet.

            Args:
                :param column_name: (str):  Column name.
                :param row_name:    (str):  Row name.

            Returns:
                (str): The cell value.
        """
        columns, _, col_index, row_index = self.get_cell_with_context(column_name, row_name)

        try:
            value = columns[col_index][row_index]
        except IndexError:
            # Cell is empty and column is stripped to not include trailing empty cells
            value = ''
        except Exception:
            print('This should not happen. Go fix your code!')
            raise
        return value


    def get_cell_index_formatted(self, column_name, row_name):
        """Finds the index of the cell by the given column and row names.

            Args:
                :param column_name: (str):  Column name.
                :param row_name:    (str):  Row name.

            Returns:
                (str): Index of the cell value in format 'Sheet1![A-ZZ][0-100000]'
        """
        _, _, col_index, row_index = self.get_cell_with_context(column_name, row_name)
        return self.__format_cell_index_to_str(col_index, row_index)


    def get_cell_with_context(self, column_name, row_name):
        """Finds the the cell by the given column and row names. Returns indices and data sheet.

            Args:
                :param column_name: (str):  Column name.
                :param row_name:    (str):  Row name.

            Returns:
                ([[]])  : data sheet grouped by columns
                ([[]])  : data sheet grouped by rows
                (str)   : searched cell column index
                (str)   : searched cell row idnex
        """
        service = self.__service
        spreadsheet_id = self.__spreadsheet_id

        rows = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=SHEET_RANGE,
            majorDimension='ROWS').execute().get('values', [])

        columns = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=SHEET_RANGE,
            majorDimension='COLUMNS').execute().get('values', [])

        if not rows or not columns:
            raise Exception('Sheet is empty. No data to process.')

        # Find column index by name
        for index, row in enumerate(rows):
            if row_name in row:
                row_index = index
                break
        else:
            raise ValueError('Invalid row name.')

        # Find row index by name
        for index, column in enumerate(columns):
            if column_name in column:
                col_index = index
                break
        else:
            raise ValueError('Invalid column name.')

        return columns, rows, col_index, row_index


    def get_whole_sheet(self):
        """ Retrieves the whole sheet by the specified URL.

            Returns:
                [[]]    : 2D list Columns-Rows
        """
        service = self.__service
        spreadsheet_id = self.__spreadsheet_id
        return service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=SHEET_RANGE,
            majorDimension='COLUMNS').execute().get('values', [])


    @staticmethod
    def __format_cell_index_to_str(col_index, row_index):
        """Converts column and row names to a formatted cell index in format 'Sheet1![A-ZZ][0-100000]'

            Args:
                :param col_index:    (str):  Column index.
                :param row_index:    (str):  Row index.

            Returns:
                (str): Formatted index of the cell value
        """
        col_index += 1
        col_name = ""
        while col_index > 0:
            col_index, remainder = divmod(col_index - 1, 26)
            col_name = chr(65 + remainder) + col_name
        return SHEET_NAME + '!' + col_name + str(row_index + 1)


    @staticmethod
    def __get_credentials(client_secret):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Credentials stored at ~/.credentials/sheets.googleapis.google-sheets-master.json

        Returns:
            Credentials, the obtained credential.
        """
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir, 'sheets.googleapis.' + CLIENT_CREDENTIALS_FILE)

        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(client_secret, SCOPES)
            flow.user_agent = APPLICATION_NAME
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else:  # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            print('Storing credentials to ' + credential_path)
        return credentials


    @staticmethod
    def __get_absolute_path(path):
        """Converts provided file path to absolute path. Throws IOError if file doesn't exist.

            Args:
                :param path (str):  Path to file. Absolute or relative.

            Returns:
                (str):  Absolute path to file.
        """
        if os.path.isabs(path) and os.path.isfile(path):
            return path
        elif path.startswith('~/'):
            # Looks like home directory
            path = os.path.expanduser(path)
        else:
            # Looks like project directory
            path = os.path.abspath(path)
        if os.path.isabs(path) and os.path.isfile(path):
            return path
        raise IOError('File not found')


if __name__ == "__main__":
    __init_args()
