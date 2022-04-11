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
        self.__participants = self.__calculate_frequency()
        
        self.__print_summary()
        
        ## apagar?
        self.df = self.__df
        self.joined = self.__joined_df
        self.left = self.__left_df
        self.sessions = self.__sessions
        self.start = self.__event_start
        self.end = self.__event_end
        self.parts = self.__participants
        
    
    def __load_csv(self):
        df = pd.read_csv(self.__report_content, parse_dates=['UTC Event Timestamp'])
        df.columns = ['SessionId', 'ParticipantId', 'FullName', 'UserAgent', 'UtcEventTimestamp', 'Action', 'Role']
        df['UtcEventTimestamp'] = df['UtcEventTimestamp'].apply(lambda x: pytz.timezone('GMT').localize(x))
        df = df.sort_values(by=['UtcEventTimestamp'])
        return df
        
        
    
    def __filter_by_action(self, action):
        keep_param = 'first' if action=="Joined" else 'last'
        
        action_sess = self.__df.query('Action==@action').rename(columns={'UtcEventTimestamp': f'{action}At'})
        action_sess = action_sess.drop_duplicates(subset='SessionId', keep=keep_param)
        action_sess = action_sess.drop(columns='Action').set_index('SessionId')
        
        return action_sess
 
    
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
        paired_sess = pd.concat([self.__joined_df, self.__left_df['LeftAt']], axis=1)
        
        is_join_late = paired_sess['JoinedAt'].apply(lambda x: True if x >= self.__event_end else False)
        is_leaving_early = paired_sess['LeftAt'].apply(lambda x: True if x <= self.__event_start else False)
        
        paired_sess['Validation'] = 'Valid'
        paired_sess.loc[is_join_late,'Validation'][is_join_late] = 'Joined late'
        paired_sess.loc[is_leaving_early, 'Validation'] = 'Left early'

        paired_sess['TruncJoinedAt'] = paired_sess['JoinedAt'].apply(lambda x: x if x>self.__event_start else self.__event_start)
        paired_sess['TruncLeftAt'] = paired_sess['LeftAt'].apply(lambda x: x if x<self.__event_end else self.__event_end)

        paired_sess.loc[is_join_late,'Validation'] = 'Joined late'
        paired_sess.loc[is_join_late,'TruncJoinedAt'] = self.__event_end
        paired_sess.loc[is_leaving_early, 'Validation'] = 'Left early'
        paired_sess.loc[is_leaving_early, 'TruncLeftAt'] = self.__event_start
        
        return paired_sess


    def __calculate_frequency(self):
        participants_sess = self.__sessions.copy()
        participants_sess = participants_sess[~participants_sess['ParticipantId'].isnull()]
        participants_sess = participants_sess[participants_sess['Validation']=='Valid']
        
        participants_ids = participants_sess['ParticipantId'].unique()
        participants_sess = participants_sess.set_index('ParticipantId')

        target_columns = ['FullName', 'Role', 'JoinedAt', 'LeftAt']
        participants_sess = participants_sess[target_columns]
        participants_sess['Duration'] = participants_sess['LeftAt'] - participants_sess['JoinedAt']
        
        freq = []

        for id in participants_ids:
            participant_slice = participants_sess.loc[id]
            if type(participant_slice)==pd.DataFrame:
                participant_slice = self.__merge_sessions(participant_slice)

            participant_slice = participant_slice.drop(['JoinedAt', 'LeftAt'])

            freq.append(participant_slice)

        return pd.DataFrame(freq)
    

    def __merge_sessions(self, df):
        session = df.iloc[0]
        joined = session['JoinedAt']
        left = session['LeftAt']
        duration = session['Duration']
        duration_arr = []

        for i, row in df.iloc[1:].iterrows():
            if row['JoinedAt'] < left:
                if row['LeftAt'] <= left:
                    pass
                else:
                    left = row['LeftAt']
                    duration = left - joined
            else:
                duration_arr.append(duration)
                joined = row['JoinedAt']
                left = row['LeftAt']
                duration = left - joined

        duration_arr.append(duration)
        duration_sum = np.array(duration_arr).sum()
        session.loc['Duration'] = duration_sum

        return session


