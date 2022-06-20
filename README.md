# Teams Attendance Report Converter


<div style="text-align:center">
    <a href="https://github.com/renefb/teams-report-converter/blob/main/README-pt-br.md">
        <img width="30" src="https://flagpedia.net/data/flags/h80/br.webp">
    </a>
    &nbsp;
    <a href="https://github.com/renefb/teams-report-converter">
        <img width="30" height="20" src="https://flagpedia.net/data/flags/h80/us.webp">
    </a>
</div>


This tool is a simple script that generates calculated attendance spreadsheets from [text attendance reports generated by MS Teams live events](https://support.microsoft.com/en-us/office/get-an-attendee-engagement-report-for-a-teams-live-event-b3101733-2eda-48a6-aeb3-de2f2bfecb3a).

It converts this:
```csv
SessionId,ParticipantId,FullName,UserAgent,UtcEventTimestamp,Action,Role
518ca2fd-...,johndoe@test.net,John Doe,Mozila/5.0...,1/25/2022 4:48:08 PM,Joined,Attendee
39f73ed2-...,mbrigs@corp.co,Mark Brigs,SignalR...,1/25/2022 4:51:13 PM,Joined,Attendee
518ca2fd-...,johndoe@test.net,John Doe,Mozila/5.0...,1/25/2022 5:25:54 PM,Left,Attendee
```
Into this:
| ParticipantId    | FullName   | Role     | AttendanceInMinutes | AttendanceFormatted |
|------------------|------------|----------|---------------------|---------------------|
| johndoe@test.net | John Doe   | Attendee | 37.1                | 000h37min04s        |
| mbrigs@corp.co   | Mark Brigs | Attendee | 65.6                | 001h05min36s        |


You can check a [live demo here](https://colab.research.google.com/drive/19sXnxrHpzvuXVnw9m61MBbmrOQX-I2J1?usp=sharing).


## Instalation

You can install this converter from [PyPI](https://pypi.org/project/teams-report-converter):

```python
pip install teams-report-converter
```


## How to use

This converter can be used as a command line application as well as a package imported by your own python application.


### Using as command line application:

```cmd
convert-teams-report -f <path-to-original-csv> -s <datetime-event-start> -e <datetime-event-end> -tz <timezone-event> -o <path-to-resulting-spreadsheet>
```
In this scenario the converter uses the following parameters:
- `-f`: path of attendance report generated by MS Teams for a live event (usually called "AttendeeReport.csv")
- `-s`: datetime of event start in the format "YYYY-MM-DD hh:mm:ss" (you must use double quotes)
- `-e`: datetime of event end in the format "YYYY-MM-DD hh:mm:ss" (you must use double quotes)
- `-o`: path of resulting spreadsheet
- `-tz`: timezone of event start and event end (for reference use [TZ database name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List))

Note that this is the unique scenario that outputs a ready to use resulting spreadsheet.


### Using as package imported by your python application

You can still use the converter as a package only for processing the original report e apply your own calculations. In this scenario, the Converter class outputs three dataframes that you can handle:

```python
from teams_report_converter import Converter

converter = Converter(report_content='AttendeeReport.csv', 
                      event_start='2021-11-03 15:00:00', 
                      event_end='2021-11-03 17:00:00', 
                      local_tz='America/Sao_Paulo')
```
From this point, you can call `converter.data` for accessing the original data. Calling `converter.sessions` outputs another dataframe listing all joins and lefts paired by sessions and `converter.attendance` outputs the dataframe that contains the total of valid minutes accumulated by each participant.


## How the tool calculates attendance

The below table shows how the timestamps from original data are processed in different scenarios:

| Joined Timestamp   | Left Timestamp                    | Truncated Joined      | Truncated Left        | Attendance Calculation                |
|:------------------:|:---------------------------------:|:---------------------:|:-----------------------:|:-------------------------------------:|
| before event start | no record                         | set to event start    | set to event end        | [event end] - [event start]           |
| before event start | before event start                | set to left timestamp | left timestamp          | [set to zero]                         |
| before event start | between event start and event end | set to event start    | left timestamp          | [left timestamp] - [event start]      |
| before event start | after event end                   | set to event start    | set to event end        | [event end] - [event start]           |
| after event start  | no record                         | joined timestamp      | set to event end        | [event end] - [joined timestamp]      |
| after event start  | before event end                  | joined timestamp      | left timestamp          | [left timestamp] - [joined timestamp] |
| after event start  | after event end                   | joined timestamp      | set to event end        | [event end] - [joined timestamp]      |
| after event end    | no record                         | joined timestamp      | set to joined timestamp | [set to zero]                         |
| after event end    | after event end                   | joined timestamp      | set to joined timestamp | [set to zero]                         |