import argparse
from datetime import datetime, date, time, timedelta
import io
import pandas as pd

from modules.report_handler import TeamsAttendeeEngagementReportHandler

   

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process MS Teams Attendee Engagement Reports.')
    parser.add_argument('-f', '--file', type=str, required=True, help='Path to the report file.')
    parser.add_argument('-s', '--start', type=str, required=True, help='Start datetime of the event in %%Y-%%m-%%d %%H:%%M format.')
    parser.add_argument('-e', '--end', type=str, required=True, help='End datetime of the event in %%Y-%%m-%%d %%H:%%M format.')
    parser.add_argument('-tz', '--timezone-name', type=str, default='UTC', help='Local timezone name of the events, like "America/Sao_Paulo" (default=UTC).\nFor more informations, see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List')
    parser.add_argument('-o', '--output', type=str, default='output.xlsx', help='Output file (default=output.xlsx).')
    args = parser.parse_args()

    # Get the report file path from the command line
    report_file_path = args.file
    # # Get the event start and end dates from the command line
    event_start = args.start
    event_end = args.end
    # # Get the local timezone from the command line
    local_tz = args.timezone_name
    # # Get the output file path from the command line
    output_file_path = args.output

    
    try:
        with open(report_file_path, 'r', encoding='utf8') as f:
            report_content = f.read()
        with io.StringIO(report_content) as buffered_content:
                report = TeamsAttendeeEngagementReportHandler(buffered_content, event_start, event_end, local_tz)
        # frequency = report.frequency.copy()
        # frequency['DurationInMinutes'] = frequency['Duration'].apply(lambda x: float('%.2f'%(x.total_seconds()/60)))
        # print(frequency)
        with pd.ExcelWriter(output_file_path) as writer:
            report.data.to_excel(writer, sheet_name='Original')
            report.sessions.to_excel(writer, sheet_name='Sessions')
            report.frequency.to_excel(writer, sheet_name='Frequency')
    
    #TODO: specify exceptions
    except Exception as e:
        print(e)
    