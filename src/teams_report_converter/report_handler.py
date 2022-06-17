from datetime import datetime
import numpy as np
import pandas as pd
import pytz

import warnings
warnings.filterwarnings("ignore")


#TODO: docstrings
#TODO: refactor original row indexing
#TODO: treat warnings in a better way
class TeamsAttendeeEngagementReportHandler:
    
    def __init__(self, report_content, event_start, event_end, local_tz='UTC'):
        self.__report_content = report_content
        self.__local_tz = local_tz
        _event_start = datetime.strptime(event_start, '%Y-%m-%d %H:%M:%S')
        self.__event_start = pytz.timezone(self.__local_tz).localize(_event_start).astimezone(pytz.timezone('UTC'))
        _event_end = datetime.strptime(event_end, '%Y-%m-%d %H:%M:%S')
        self.__event_end = pytz.timezone(self.__local_tz).localize(_event_end).astimezone(pytz.timezone('UTC'))
                
        self.data = self.__load_csv()
        self.__joined_df = self.__filter_by_action('Joined')
        self.__left_df = self.__filter_by_action('Left')
        self.sessions = self.__pair_sessions()
        self.attendance = self.__calculate_attendance()

        self.joined_df = self.__joined_df
        self.left_df = self.__left_df

        self.data = self.__remove_tzinfo(self.data)
        self.sessions = self.__remove_tzinfo(self.sessions)
      
  

    def __load_csv(self):
        df = pd.read_csv(self.__report_content, parse_dates=['UTC Event Timestamp'])
        # keep 'UserAgent', 'Role' and 'Action' collumn names, rename others
        columns_mapper = {
            'Session Id': 'SessionId',
            'Participant Id': 'ParticipantId',
            'Full Name': 'FullName',
            'UTC Event Timestamp': 'UtcEventTimestamp'
        }
        df = df.rename(columns=columns_mapper)
        # df.index += 1
        # df.index.names = ['OriginalRow']
        df['UtcEventTimestamp'] = df['UtcEventTimestamp'].apply(lambda x: pytz.timezone('UTC').localize(x))
        
        return df
        
        
    
    def __filter_by_action(self, action):
        keep_param = 'first' if action=="Joined" else 'last'
        
        df_action = self.data.query('Action==@action').rename(columns={'UtcEventTimestamp': action})
        df_action = df_action.drop_duplicates(subset='SessionId', keep=keep_param)
        df_action = df_action.drop(columns='Action').set_index('SessionId')

        ordered_cols = ['ParticipantId', 'FullName', 'Role', 'UserAgent', action]        
        return df_action[ordered_cols]
 
    

    def __pair_sessions(self):
        paired_sess = pd.concat([self.__joined_df, self.__left_df['Left']], axis=1)
        df_sess = pd.DataFrame()
        
        dt_infinity = pd.to_datetime('2199-12-31 23:59:59')
        dt_infinity = pytz.timezone('UTC').localize(dt_infinity)
        paired_sess['Left'].fillna(dt_infinity, inplace=True)

        for _, row in paired_sess.iterrows():

            joined_at = row['Joined']
            left_at = row['Left'] #if pd.notnull(row['Left']) else dt_infinity

            row['TruncJoined'] = max(joined_at, min(left_at, self.__event_start))
            row['TruncLeft'] = min(left_at, max(joined_at, self.__event_end))
        
            if row['TruncLeft'] < self.__event_start:
                row['Validation'] = 'Left early'
            elif row['TruncJoined'] > self.__event_end:
                row['Validation'] = 'Joined late'
            else:
                row['Validation'] = 'Valid'
            
            df_sess = df_sess.append(row)

        # df_sess['Left'] = df_sess['Left'].apply(lambda x: pytz.timezone('UTC').localize(x))
                
        if self.__local_tz not in ('UTC', 'GMT'):
            df_sess['TzTruncJoined'] = df_sess['TruncJoined'].dt.tz_convert(self.__local_tz)
            df_sess['TzTruncLeft'] = df_sess['TruncLeft'].dt.tz_convert(self.__local_tz)
        
        idx_col_validation = np.where(df_sess.columns=='Validation')[0][0]
        ordered_cols = np.append(np.delete(df_sess.columns, idx_col_validation), 'Validation')   

        return df_sess[ordered_cols].reset_index().rename(columns={'index': 'SessionId'})



    def __calculate_attendance(self):
        df_sess = self.sessions.copy()
        df_sess = df_sess[~df_sess['ParticipantId'].isnull()]

        participants_ids = df_sess['ParticipantId'].unique()
        df_sess = df_sess.set_index('ParticipantId')
        df_sess.index.names = ['ParticipantId']

        target_columns = ['FullName', 'Role', 'TruncJoined', 'TruncLeft']
        df_sess = df_sess[target_columns]
        df_sess['Duration'] = df_sess['TruncLeft'] - df_sess['TruncJoined']
        
        attend = []

        for pid in participants_ids:
            record = df_sess.loc[pid]
            if type(record)==pd.DataFrame:
                record = self.__merge_sessions(df_sess.loc[pid])
            record = record.drop(['TruncJoined', 'TruncLeft'])
            attend.append(record)

        df_attend = pd.DataFrame(attend)
        df_attend['AttendanceInMinutes'] = df_attend['Duration'].apply(lambda x: round(x.total_seconds()/60, 2))
        df_attend.drop(columns=['Duration'], inplace=True)
        df_attend = df_attend.sort_values(by=['FullName'])
        df_attend = df_attend.reset_index().rename(columns={'index': 'ParticipantId'})
        reordered_cols = ['FullName', 'ParticipantId', 'Role', 'AttendanceInMinutes']
        
        return df_attend[reordered_cols]
    


    def __merge_sessions(self, df):
        record = df.iloc[0]
        joined = record['TruncJoined']
        left = record['TruncLeft']
        duration = record['Duration']
        duration_arr = []

        for _, row in df.iloc[1:].iterrows():
            if row['TruncJoined'] < left:
                if row['TruncLeft'] <= left:
                    pass
                else:
                    left = row['TruncLeft']
                    duration = left - joined
            else:
                duration_arr.append(duration)
                joined = row['TruncJoined']
                left = row['TruncLeft']
                duration = left - joined

        duration_arr.append(duration)
        duration_sum = np.array(duration_arr).sum()
        record.loc['Duration'] = duration_sum

        return record



    def __summary(self):
        width = 50
        summary = {
            'start_end': {
                'Informed event start': self.__event_start,
                'Informed event end': self.__event_end
            },
            'records': {
                'Rows': str(self.data.shape[0])
            },
            'join': {
                'Joined rows': self.__joined_df.shape[0],
                ' - First at': self.__joined_df['Joined'].min(),
                ' - Last at': self.__joined_df['Joined'].max(),
            },
            'left': {
                'Left rows': self.__left_df.shape[0],
                ' - First at': self.__left_df['Left'].min(),
                ' - Last at': self.__left_df['Left'].max()
            },
            'sessions': {
                'Unique sessions': len(self.data['SessionId'].unique()),
                ' - Left before event start': (self.sessions['Validation']=='Left early').sum(),
                ' - Joined after event end': (self.sessions['Validation']=='Joined late').sum(),
                ' - Without Participant Id': self.sessions['ParticipantId'].isnull().sum(),
            },
            'participants': {
                'Unique participants': len(self.sessions['ParticipantId'].unique()) - 1  # -1 for the unknown participant
            }
        }

        print('S U M M A R Y'.center(width))
        print('-'*width)        
        for _, section_values in summary.items():
            for k, v, in section_values.items():
                len_k = len(k)
                print(k, str(v).rjust(width - len_k - 1))
            print('-'*width)
        
    
        
    def __remove_tzinfo(self, df):
        for col in df.select_dtypes(include=['datetime64[ns, UTC]']).columns:
            df[col] = df[col].apply(lambda x: x.replace(tzinfo=None))
        return df
