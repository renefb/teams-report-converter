import datetime
import numpy as np
import pandas as pd
import pytz


class TeamsAttendeeEngagementReportHandler:
    
    def __init__(self, report_content, event_start, event_end, local_tz='GMT'):
        self.__report_content = report_content
        # self.__report_tz = pytz.timezone('GMT')
        self.__event_start = pd.Timestamp(event_start, tz=local_tz).astimezone(pytz.timezone('GMT'))
        self.__event_end = pd.Timestamp(event_end, tz=local_tz).astimezone(pytz.timezone('GMT'))
        self.__tz_localizer = pytz.timezone(local_tz)
                
        self.__df = self.__load_csv()
        self.__joined_df = self.__filter_by_action('Joined')
        self.__left_df = self.__filter_by_action('Left')
        self.__sessions = self.__pair_sessions()
        self.__frequency = self.__calculate_frequency()
        
        self.__print_summary()
        
        ## apagar?
        self.df = self.__df
        self.joined = self.__joined_df
        self.left = self.__left_df
        self.sessions = self.__sessions
        self.start = self.__event_start
        self.end = self.__event_end
        self.parts = self.__frequency
        
    
    def __load_csv(self):
        df = pd.read_csv(self.__report_content, parse_dates=['UTC Event Timestamp'])
        df.columns = ['SessionId', 'ParticipantId', 'FullName', 'UserAgent', 'UtcEventTimestamp', 'Action', 'Role']
        df['UtcEventTimestamp'] = df['UtcEventTimestamp'].apply(lambda x: pytz.timezone('GMT').localize(x))
        df = df.sort_values(by=['UtcEventTimestamp'])
        return df
        
        
    
    def __filter_by_action(self, action):
        action_col = f'{action}At'
        keep_param = 'first' if action=="Joined" else 'last'
        
        df_action = self.__df.query('Action==@action').rename(columns={'UtcEventTimestamp': action_col})
        df_action = df_action.drop_duplicates(subset='SessionId', keep=keep_param)
        df_action = df_action.drop(columns='Action').set_index('SessionId')

        ordered_cols = ['ParticipantId', 'FullName', 'Role', 'UserAgent', action_col]        
        return df_action[ordered_cols]
 
    
    def __print_summary(self):
        width = 50
        summary = {
            'start_end': {
                'Informed event start': self.__event_start,
                'Informed event end': self.__event_end
            },
            'records': {
                'Rows': str(self.__df.shape[0])
            },
            'join': {
                'Joined rows': self.__joined_df.shape[0],
                ' - First at': self.__joined_df['JoinedAt'].min(),
                ' - Last at': self.__joined_df['JoinedAt'].max(),
            },
            'left': {
                'Left rows': self.__left_df.shape[0],
                ' - First at': self.__left_df['LeftAt'].min(),
                ' - Last at': self.__left_df['LeftAt'].max()
            },
            'sessions': {
                'Unique sessions': len(self.__df['SessionId'].unique()),
                ' - Left before event start': (self.__sessions['Validation']=='Left early').sum(),
                ' - Joined after event end': (self.__sessions['Validation']=='Joined late').sum(),
                ' - Without Participant Id': self.__sessions['ParticipantId'].isnull().sum(),
            },
            'participants': {
                'Unique participants': len(self.__sessions['ParticipantId'].unique())
            }
        }

        print('S U M M A R Y'.center(width))
        print('-'*width)        
        for section_names, section_values in summary.items():
            for k, v, in section_values.items():
                len_k = len(k)
                print(k, str(v).rjust(width - len_k - 1))
            print('-'*width)
        
    
        
    def __pair_sessions(self):
        df_sess = pd.concat([self.__joined_df, self.__left_df['LeftAt']], axis=1)
        
        # is_join_late = df_sess['JoinedAt'].apply(lambda x: True if x >= self.__event_end else False)
        # is_leaving_early = df_sess['LeftAt'].apply(lambda x: True if x <= self.__event_start else False)
        
        # df_sess['TruncJoined'] = df_sess['JoinedAt'].apply(lambda x: x if x>self.__event_start else self.__event_start)
        # df_sess['TruncLeft'] = df_sess['LeftAt'].apply(lambda x: x if x<self.__event_end else self.__event_end)
        
        # df_sess['Validation'] = 'Valid'
        # df_sess.loc[is_join_late,'Validation'] = 'Joined late'
        # df_sess.loc[is_join_late,'TruncJoined'] = self.__event_end

        # df_sess.loc[is_leaving_early, 'Validation'] = 'Left early'
        # df_sess.loc[is_leaving_early, 'TruncLeftAt'] = self.__event_start

        df_sess['TruncJoined'] = df_sess['JoinedAt']
        df_sess['TruncLeft'] = df_sess['LeftAt']
        df_sess['LocalTruncJoined'] = df_sess['JoinedAt']
        df_sess['LocalTruncLeft'] = df_sess['LeftAt']
        df_sess['Validation'] = 'Valid'

        for idx, row in df_sess.iterrows():
            if row['TruncJoined'] < self.__event_start:
                df_sess.loc[idx, 'TruncJoined'] = self.__event_start
                if row['TruncLeft'] < self.__event_start:
                    df_sess.loc[idx, 'Validation'] = 'Left early'
                    df_sess.loc[idx, 'TruncJoined'] = df_sess.loc[idx, 'TruncLeft']
            elif row['TruncLeft'] > self.__event_end:
                df_sess.loc[idx, 'TruncLeft'] = self.__event_end
                if row['TruncJoined'] > self.__event_end:
                    df_sess.loc[idx, 'Validation'] = 'Joined late'
                    df_sess.loc[idx, 'TruncLeft'] = df_sess.loc[idx, 'TruncJoined']

        return df_sess


    def __calculate_frequency(self):
        df_sess = self.__sessions.copy()
        df_sess = df_sess[~df_sess['ParticipantId'].isnull()]

        # df_sess['TruncJoinedAt'] = df_sess['JoinedAt'].apply(lambda x: x if x>self.__event_start else self.__event_start)
        # df_sess['TruncLeftAt'] = df_sess['LeftAt'].apply(lambda x: x if x<self.__event_end else self.__event_end)

        # df_sess.loc[df_sess['TruncJoinedAt'] > self.__event_end,'TruncJoinedAt'] = self.__event_end
        # df_sess.loc[df_sess['TruncLeftAt'] < self.__event_start, 'TruncLeftAt'] = self.__event_start
        
        # participants_sess = participants_sess[participants_sess['Validation']=='Valid']
        
        participants_ids = df_sess['ParticipantId'].unique()
        df_sess = df_sess.set_index('ParticipantId')
        df_sess.index.names = ['ParticipantId']

        target_columns = ['FullName', 'Role', 'TruncJoined', 'TruncLeft']
        df_sess = df_sess[target_columns]
        df_sess['Duration'] = df_sess['TruncLeft'] - df_sess['TruncJoined']
        
        freq = []

        for id in participants_ids:
            record = df_sess.loc[id]
            if type(record)==pd.DataFrame:
                record = self.__merge_sessions(df_sess.loc[id])
            record = record.drop(['TruncJoined', 'TruncLeft'])
            freq.append(record)

        df_freq = pd.DataFrame(freq)
        # df_freq = df_freq.reset_index()
        df_freq = df_freq.sort_values(by=['FullName'])
        return df_freq
    

    def __merge_sessions(self, df):
        record = df.iloc[0]
        joined = record['TruncJoined']
        left = record['TruncLeft']
        duration = record['Duration']
        duration_arr = []

        # print('starting with' session.name, joined)

        for i, row in df.iloc[1:].iterrows():
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


